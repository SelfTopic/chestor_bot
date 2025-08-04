from aiogram import BaseMiddleware 
from typing import Callable, Awaitable, Dict, Any
from aiogram.types import TelegramObject

from ..services import SyncEntitiesService
from ..containers import Container

from dependency_injector.wiring import Provide
import logging 

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
        await sync_entites_sevices.sync(event)
        await handler(event, data)