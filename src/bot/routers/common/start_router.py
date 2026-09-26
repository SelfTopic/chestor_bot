from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Command, HasUser

from ...context import AppContext
from ..types import UserMessage


class StartHandler(MessageHandler[AppContext[UserMessage]]):
    # CommandStart(deep_link=False) в aiogram принимает и /start, и /start payload
    query = Command("start") & HasUser()

    async def handle(self) -> None:
        user = await self.ctx.db_user()

        await self.ctx.message.answer(
            self.ctx.dialog_service.text(key="start", name=user.first_name or "User")
        )


class StartRouter(BaseRouter[AppContext]):
    handlers = (StartHandler,)
