from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Text

from src.bot.dialogs import Dialogs
from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext
from ..types import TextMessage


class CheckRulesHandler(MessageHandler[AppContext[TextMessage]]):
    query = Text("правила", ignore_case=True)

    async def handle(self) -> None:
        message = self.ctx.message
        chat = await self.ctx.chat_service.get_by_telegram_id(
            telegram_id=message.chat.id
        )

        if not chat:
            raise ChatNotFoundInDatabase()

        if not chat.rules:
            await message.answer(self.ctx.text(Dialogs.rules.missing()))
            return

        await message.answer(chat.rules)


class CheckRulesRouter(BaseRouter[AppContext]):
    handlers = (CheckRulesHandler,)
