import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from dependency_injector.wiring import Provide

from ..containers import Container
from ..services import RpCommandsService

logger = logging.getLogger(__name__)


class RpCommandsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
        rp_commands_service: RpCommandsService = Provide[Container.rp_commands_service],
    ) -> None:
        logger.debug("Calling rp command service load cache")

        if isinstance(event, Message):
            chat_id = event.chat.id
            rp_commands = await rp_commands_service.get_all(chat_id=chat_id)
            data["rp_commands"] = rp_commands
            logger.debug("Cache is loaded or exists")
        await handler(event, data)
