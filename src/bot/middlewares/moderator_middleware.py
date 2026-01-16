import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class ModeratorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> None:
        logger.debug("Calling moderator middleware.")

        chat_type = "private"
        user, chat = None, None

        if isinstance(event, Message):
            chat_type = event.chat.type
            user = event.from_user
            chat = event.chat

        if isinstance(event, CallbackQuery) and isinstance(event.message, Message):
            chat_type = event.message.chat.type
            chat = event.message.chat
            user = event.from_user

        if chat_type != "supergroup":
            pass

        if (not chat) or (not user):
            raise ValueError("Chat or User objects not found")

        bot: Bot | None = data.get("bot")

        if not bot:
            logger.error("Object of bot not found in middleware data.")
            raise RuntimeError("Object of bot not found in middleware data.")

        member = await bot.get_chat_member(chat_id=chat.id, user_id=user.id)

        if member.status not in ["administrator", "creator"]:
            return

        await handler(event, data)

        logger.debug("End called of moderator middleware")
