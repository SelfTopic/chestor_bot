from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Command

from ...context import AppContext
from ..types import TextMessage


class HelpHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("help")

    async def handle(self) -> None:
        await self.ctx.message.answer(
            self.ctx.dialog_service.text(
                key="help",
                commands_link="https://t.me/CheStorCommands",
                lore_link="Временно отсутствует",
            )
        )


class HelpRouter(BaseRouter[AppContext]):
    handlers = (HelpHandler,)
