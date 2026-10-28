from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.dialogs import Dialogs
from src.bot.utils import format_amount

from ...context import AppContext
from ..types import UserMessage


class BalanceHandler(MessageHandler[AppContext[UserMessage]]):
    query = (Text("бал", ignore_case=True) | Text("bal", ignore_case=True)) & HasUser()

    async def handle(self) -> None:
        user = await self.ctx.db_user()
        balance = await self.ctx.user_service.balance(user.telegram_id)

        await self.ctx.say(
            Dialogs.balance(balance=format_amount(balance), name=user.first_name)
        )


class BalanceRouter(BaseRouter[AppContext]):
    handlers = (BalanceHandler,)
