from pydantic import Field
from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from src.bot.dialogs import Dialogs
from src.bot.utils import format_amount

from ...context import AppContext
from ...repositories import TopWallet
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
                    place=place,
                    name=self.wallet_name(wallet),
                    balance=format_amount(wallet.balance),
                )
            )
            for place, wallet in enumerate(top, start=1)
        )
        await self.ctx.say(Dialogs.tops.balance.message(count=count, rows=rows))

    def wallet_name(self, wallet: TopWallet) -> str:
        if not wallet.is_family:
            return wallet.names[0]
        if wallet.family_name:
            return wallet.family_name
        return self.ctx.text(Dialogs.family.top_name(members=", ".join(wallet.names)))

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(self.range_error, reply=True)
            return

        raise exc


class CommonTopsRouter(BaseRouter[AppContext]):
    handlers = (TopBalanceHandler,)
