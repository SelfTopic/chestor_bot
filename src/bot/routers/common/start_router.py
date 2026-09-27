from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Command, HasUser

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import UserMessage


class StartHandler(MessageHandler[AppContext[UserMessage]]):
    query = Command("start") & HasUser()

    async def handle(self) -> None:
        user = await self.ctx.db_user()

        await self.ctx.message.answer(
            self.ctx.text(Dialogs.start(name=user.first_name or "User"))
        )


class StartRouter(BaseRouter[AppContext]):
    handlers = (StartHandler,)
