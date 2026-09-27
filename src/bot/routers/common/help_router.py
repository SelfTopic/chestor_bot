from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Command

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import TextMessage


class HelpHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("help")

    async def handle(self) -> None:
        await self.ctx.message.answer(self.ctx.text(Dialogs.help()))


class HelpRouter(BaseRouter[AppContext]):
    handlers = (HelpHandler,)
