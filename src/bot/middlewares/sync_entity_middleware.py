import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from dependency_injector.wiring import Provide

from ..containers import Container
from ..services import SyncEntitiesService

logger = logging.getLogger(__name__)

class SyncEntitiesMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
        sync_entites_sevices: SyncEntitiesService = Provide[Container.sync_entities_service]
    ) -> None:
        
        logger.debug("Calling sync entities")
        await sync_entites_sevices.sync(event=event, bot=data["bot"])
        await handler(event, data)