from .base import Base 
from src.bot.utils import parse_seconds
from typing import Union

import logging 
import time

logger = logging.getLogger(__name__)

class CooldownService(Base):

    async def get_cooldown(
        self,
        cooldown_name: str | None = None,
        cooldown_id: int | None = None
    ):
        
        parameter = cooldown_name or cooldown_id

        if not parameter:

            raise ValueError("Arguments is invalid")

        cooldown = await self.cooldown_repository\
            .get_cooldown(
                search_parameter=parameter
            )

        return cooldown
    
    async def set_cooldown(
        self,
        telegram_id: int,
        cooldown_type: str
    ):
        
        cooldown = await self.cooldown_repository.set_cooldown(
            user_id=telegram_id,
            cooldown_type=cooldown_type
        )

        return cooldown
    
    async def reset_cooldown(
        self,
        telegram_id: int,
        cooldown_type: str  
    ):
        user = await self.user_repository.get(search_parameter=telegram_id)

        if not user:
            logger.error("User not found in database")
            raise ValueError("User not found in database")
        

        new_cooldown = await self.cooldown_repository.reset_cooldown(
            user_id=user.id,
            cooldown_type=cooldown_type
        )

        return new_cooldown


    async def is_end_cooldown(
        self,
        telegram_id: int,
        cooldown_type: str
    ):
        is_cooldown = await self.cooldown_repository\
            .is_cooldown_active(
                user_id=telegram_id,
                cooldown_type=cooldown_type
            )
        
        return bool