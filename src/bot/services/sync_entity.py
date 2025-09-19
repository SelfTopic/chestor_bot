from .base import Base 
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
import logging

logger = logging.getLogger(__name__)

class SyncEntitiesService(Base):

    async def sync(self, event: TelegramObject) -> None:
        logger.debug(f"Called method sync. Event type: {type(event).__name__}")
        
        if (
            isinstance(event, Update) and 
            (isinstance(event.event, Message) or isinstance(event.event, CallbackQuery))
            ) and event.event.from_user:
            
            logger.debug(f"Processing user sync. User ID: {event.event.from_user.id}")
            
            await self.user_repository.upsert(
                telegram_id=event.event.from_user.id,
                first_name=event.event.from_user.first_name,
                last_name=event.event.from_user.last_name,
                username=event.event.from_user.username  
            )
            
            logger.debug("User synchronized successfully")
            return 
        
        logger.debug("Event type not equal message or callback query")

__all__ = ["SyncEntitiesService"]