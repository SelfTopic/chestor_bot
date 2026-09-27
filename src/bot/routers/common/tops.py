from pydantic import Field
from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import TextMessage


class TopArgs(CommandArgs):
    count: int = Field(20, ge=1, le=50)
    extra: Rest = ""


class TopBalanceHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("топ бал", TopArgs, prefixes="", ignore_case=True)
    query = cmd
    range_error = Dialogs.tops.balance.bad_count()

    async def handle(self) -> None:
        count = self.cmd.parse(self.ctx).count

        top = await self.ctx.user_service.get_top_balance(count)

        rows = "\n".join(
            self.ctx.text(
                Dialogs.tops.balance.row(
                    place=place, name=user.first_name, balance=user.balance
                )
            )
            for place, user in enumerate(top, start=1)
        )
        await self.ctx.message.answer(
            self.ctx.text(Dialogs.tops.balance.text(count=count, rows=rows))
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.ctx.text(self.range_error))
            return

        raise exc


class CommonTopsRouter(BaseRouter[AppContext]):
    handlers = (TopBalanceHandler,)
