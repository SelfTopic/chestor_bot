from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import UserMessage


class BalanceHandler(MessageHandler[AppContext[UserMessage]]):
    query = Text("бал", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        user = await self.ctx.db_user()

        await self.ctx.answer_message(
            self.ctx.dialog_service.text(
                Dialogs.balance(balance=str(user.balance), name=user.first_name)
            )
        )


class BalanceRouter(BaseRouter[AppContext]):
    handlers = (BalanceHandler,)
