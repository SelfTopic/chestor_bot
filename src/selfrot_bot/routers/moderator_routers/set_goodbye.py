from selfrot import MessageHandler
from selfrot.filter import TextStartswith

from ...context import AppContext
from ...types import TextMessage
from .set_chat_text import SetChatTextHandler


class SetGoodbyeHandler(SetChatTextHandler, MessageHandler[AppContext[TextMessage]]):
    PREFIX = "новое прощание"
    query = TextStartswith(PREFIX, ignore_case=True)

    async def apply(self, telegram_id: int, value: str) -> str:
        chat = await self.ctx.chat_service.set_chat_goodbye_message(telegram_id, value)
        return f"Прощальное сообщение обновлено: \n\n{chat.goodbye_message}"
