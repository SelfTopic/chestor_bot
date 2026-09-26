from pydantic import Field
from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from ...context import AppContext
from ..types import TextMessage


class TopArgs(CommandArgs):
    count: int = Field(20, ge=1, le=50)
    extra: Rest = ""  # всё после числа игнорируется, как у прода


class TopBalanceHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("топ бал", TopArgs, prefixes="", ignore_case=True)
    query = cmd
    range_error = "Топ нужно указывать положительной цифрой в диапазоне 1-50"

    async def handle(self) -> None:
        count = self.cmd.parse(
            self.ctx
        ).count  # не число или вне 1-50: CommandArgsError

        top = await self.ctx.user_service.get_top_balance(count)

        text = f"Топ {count} самых богатих гулий: \n\n"
        for i, user in enumerate(top, start=1):
            text += f"{i}. {user.first_name} - {user.balance} CheSton\n"

        await self.ctx.message.answer(text)

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.range_error)
            return

        raise exc


class CommonTopsRouter(BaseRouter[AppContext]):
    handlers = (TopBalanceHandler,)
