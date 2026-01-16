import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from src.config import settings

logger = logging.getLogger(__name__)


class CreatorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> None:
        is_message = isinstance(event, Message)
        is_callback = isinstance(event, CallbackQuery)

        if (is_message or is_callback) and event.from_user:
            if event.from_user.id not in settings.ADMIN_IDS:
                return None

            await handler(event, data)

        return None
