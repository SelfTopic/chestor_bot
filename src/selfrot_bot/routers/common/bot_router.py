from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Text

from ...context import AppContext
from ..types import TextMessage


class BotHandler(MessageHandler[AppContext[TextMessage]]):
    query = Text("бот", ignore_case=True)

    async def handle(self) -> None:
        await self.ctx.message.answer(self.ctx.dialog_service.random(key="bot"))


class BotRouter(BaseRouter[AppContext]):
    handlers = (BotHandler,)
