from .base import Base 
from aiogram.types import User as TelegramUser
from ...database.models import User

from typing import Optional, Union

import logging 

logger = logging.getLogger(__name__)

class UserService(Base):
    """Service for managing user data"""
    
    async def upsert(
        self, 
        telegram_user_data: TelegramUser
    ) -> Optional[User]:
        logger.debug("Called method register")

        # Don't register bots
        if telegram_user_data.is_bot == True:
            return None

        user = await self.user_repository\
            .upsert(
                telegram_id=telegram_user_data.id,
                first_name=telegram_user_data.first_name,
                last_name=telegram_user_data.last_name,
                username=telegram_user_data.username    
            )
        
        logger.debug(f"Added/updated new user (id={user.telegram_id}) in database")
        
        return user
    
    async def get(self, find_by: Union[str, int]) -> Optional[User]:

        logger.debug("Called method get")

        user = await self.user_repository.get(
            search_parameter=find_by
        )

        return user
    
    # Methods for update data of users
    async def update_balance(self): ...
    async def update_energy(self): ...
    
__all__ = ["UserService"]