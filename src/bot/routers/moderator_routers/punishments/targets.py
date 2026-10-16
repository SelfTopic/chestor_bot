import re
from typing import Any, Generic, TypeVar

from selfrot import CommandArgs, MessageHandler, Rest
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
    return query, cut(text, match.start(), match.end())


def cut(text: str, start: int, end: int) -> str:
    return " ".join((text[:start] + " " + text[end:]).split())


def without_name(text: str, name: str) -> str:
    start = text.find(name)
    return text if start < 0 else cut(text, start, start + len(name))


class TargetTextArgs(CommandArgs):
    text: Rest = ""


TContext = TypeVar("TContext", bound=AppContext[Any])


class AnywhereTargetHandler(MessageHandler[TContext], Generic[TContext]):
    cmd: AnyCommand[TargetTextArgs]

    def not_found(self, target: str) -> Line:
        raise NotImplementedError

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).text
        # Кликабельное имя человека без ника несёт его id: искать в базе не нужно.
        mentioned = self.ctx.mentions()
        if mentioned:
            name, user = mentioned[0]
            await self.perform(user.id, without_name(text, name))
            return

        found = split_target(text)
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
