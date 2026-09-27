from selfrot import MessageHandler

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import TextMessage
from .set_chat_text import SetChatTextHandler, chat_text_command


class SetRulesHandler(SetChatTextHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = chat_text_command("новые правила")
    query = cmd

    async def apply(self, telegram_id: int, value: str) -> str:
        chat = await self.ctx.chat_service.set_chat_rules(telegram_id, value)
        return self.ctx.text(Dialogs.moderation.rules_updated(rules=chat.rules))
