from selfrot import MessageHandler

from ...context import AppContext
from ..types import TextMessage
from .set_chat_text import SetChatTextHandler, chat_text_command


class SetWelcomeHandler(SetChatTextHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = chat_text_command("новое приветствие")
    query = cmd

    async def apply(self, telegram_id: int, value: str) -> str:
        chat = await self.ctx.chat_service.set_chat_welcome_message(telegram_id, value)
        return f"Приветственное сообщение обновлено: \n\n{chat.welcome_message}"
