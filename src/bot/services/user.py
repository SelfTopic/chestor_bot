from .base import Base 

from aiogram.types import User as TelegramUser
from src.database.models import User
from typing import Optional, Union
from ..types import Race
import logging 

logger = logging.getLogger(__name__)

class UserService(Base):

    async def upsert(self, telegram_user_data: TelegramUser) -> Optional[User]:
        logger.debug(f"Called method upsert. User ID: {telegram_user_data.id}")
        
        if telegram_user_data.is_bot == True:
            logger.debug("User is bot, skipping registration")
            return None

        user = await self.user_repository.upsert(
            telegram_id=telegram_user_data.id,
            first_name=telegram_user_data.first_name,
            last_name=telegram_user_data.last_name,
            username=telegram_user_data.username    
        )
        
        logger.debug(f"Added/updated user (id={user.telegram_id}) in database")
        return user
    
    async def get(self, find_by: Union[str, int]) -> Optional[User]:
        logger.debug(f"Called method get. Search parameter: {find_by}")
        
        user = await self.user_repository.get(search_parameter=find_by)
        
        logger.debug(f"User found: {user is not None}")
        return user
    
    async def plus_balance(
        self, 
        telegram_id: int, 
        change_balance: int
    ) -> User:
        logger.debug(f"Called method plus_balance. User ID: {telegram_id}, change balance: {change_balance}")

        user = await self.get(find_by=telegram_id)

        if not user:
            logger.error("Cannot change balance to nouser")
            raise ValueError("Cannot change balance to nouser")

        user = await self.user_repository.change_data(
            telegram_id=telegram_id,
            balance=user.balance + change_balance
        )

        return user
    
    async def minus_balance(
        self,
        telegram_id: int,
        change_balance: int        
    ) -> User:
        
        logger.debug(f"Called method minus_balance. User ID: {telegram_id}, change balance: {change_balance}")

        user = await self.get(find_by=telegram_id)

        if not user:
            logger.error("Cannot change balance to nouser")
            raise ValueError("Cannot change balance to nouser")
        
        user = await self.user_repository.change_data(
            telegram_id=telegram_id,
            balance=user.balance - change_balance    
        )
        
        return user
    
    def race(self, bit: int) -> Optional[Race]:

        for race in Race:
            if race.value['bit'] == bit:
                return race
            
        return None
    

__all__ = ["UserService"]