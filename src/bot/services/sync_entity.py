import logging

from aiogram import Bot
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from ..types.insert import ChatInsert
from .base import Base

logger = logging.getLogger(__name__)

class SyncEntitiesService(Base):

    async def sync(self, event: TelegramObject, bot: Bot) -> None:
        logger.debug(f"Called method sync. Event type: {type(event).__name__}")
        
        if (isinstance(event, Update) and 
            (isinstance(event.event, Message) or isinstance(event.event, CallbackQuery))
            ) and event.event.from_user:
            
            logger.debug(f"Processing user sync. User ID: {event.event.from_user.id}")
            
            await self.user_repository.upsert(
                telegram_id=event.event.from_user.id,
                first_name=event.event.from_user.first_name,
                last_name=event.event.from_user.last_name,
                username=event.event.from_user.username  
            )

        if (isinstance(event, Update) and 
            (isinstance(event.event, Message))
            ):

            administrators = await bot.get_chat_administrators(event.event.chat.id)
            creator = administrators[0]
            for admin in administrators:
                if admin.status == ChatMemberStatus.CREATOR:
                    creator = admin
                    break 

            chat_insert_data = ChatInsert(
                telegram_id=event.event.chat.id,
                title=event.event.chat.title,
                username=event.event.chat.username,
                creator_id=creator.user.id
            )

            await self.chat_repository.upsert(chat_insert_data)
            

__all__ = ["SyncEntitiesService"]