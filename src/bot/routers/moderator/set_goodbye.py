from selfrot import MessageHandler

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import TextMessage
from .set_chat_text import SetChatTextHandler, chat_text_command


class SetGoodbyeHandler(SetChatTextHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = chat_text_command("новое прощание")
    query = cmd

    async def apply(self, telegram_id: int, value: str) -> str:
        chat = await self.ctx.chat_service.set_chat_goodbye_message(telegram_id, value)
        return self.ctx.text(
            Dialogs.moderation.goodbye_updated(text=chat.goodbye_message)
        )
