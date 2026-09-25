from selfrot import MessageHandler
from selfrot.filter import TextStartswith

from ...context import AppContext
from ...types import TextMessage
from .set_chat_text import SetChatTextHandler


class SetRulesHandler(SetChatTextHandler, MessageHandler[AppContext[TextMessage]]):
    PREFIX = "новые правила"
    query = TextStartswith(PREFIX, ignore_case=True)

    async def apply(self, telegram_id: int, value: str) -> str:
        chat = await self.ctx.chat_service.set_chat_rules(telegram_id, value)
        return f"Правила чата обновлены: \n\n{chat.rules}"
