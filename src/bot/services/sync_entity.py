from .base import Base 
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

import logging

logger = logging.getLogger(__name__)

class SyncEntitiesService(Base):

    async def sync(self, event: TelegramObject) -> None:

        logger.debug("Called method sync")

        if (
            isinstance(event, Update) and 
            (isinstance(event.event, Message) or isinstance(event.event, CallbackQuery))
            ) and event.event.from_user:
            logger.debug("Calling method upsert from repo")
            await self.userRepository.upsert(
                telegram_id=event.event.from_user.id,
                first_name=event.event.from_user.first_name,
                last_name=event.event.from_user.last_name,
                username=event.event.from_user.username  
            )

            return 
        
        logger.debug("Event type not equal message or callback query")

        

__all__ = ["SyncEntitiesService"]