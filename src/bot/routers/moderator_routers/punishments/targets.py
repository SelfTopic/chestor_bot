import re
from typing import Any

from selfrot import CommandArgs, Rest
from selfrot.filter import AnyCommand

from src.bot.dialogs import Line
from src.bot.exceptions import TargetMissing

from ....context import AppContext
from ....services.lookup import find_user

# Ник Telegram однозначен в любом месте текста. Число — только первым словом: иначе
# в «мут 30 сек» тридцатку приняли бы за id.
USERNAME = re.compile(r"(?<!\S)@\w{4,32}(?!\S)")
LEADING_ID = re.compile(r"^\s*(-?\d+)(?!\S)")


def split_target(text: str) -> tuple[str, str] | None:
    match = USERNAME.search(text) or LEADING_ID.match(text)
    if match is None:
        return None

    query = match.group(1) if match.re is LEADING_ID else match.group(0)
    rest = text[: match.start()] + " " + text[match.end() :]
    return query, " ".join(rest.split())


class TargetTextArgs(CommandArgs):
    text: Rest = ""


# Миксин не наследует MessageHandler: selfrot проверяет заголовок только на прямых базах.
class AnywhereTargetHandler:
    ctx: AppContext[Any]
    cmd: AnyCommand[TargetTextArgs]

    def not_found(self, target: str) -> Line:
        raise NotImplementedError

    async def handle(self) -> None:
        found = split_target(self.cmd.parse(self.ctx).text)
        if found is None:
            raise TargetMissing()

        query, rest = found
        user = await find_user(self.ctx.user_service, query)
        if user is None:
            await self.ctx.say(self.not_found(query), reply=True)
            return

        await self.perform(user.telegram_id, rest)

    async def perform(self, telegram_id: int, rest: str) -> None:
        raise NotImplementedError
