import logging
from typing import Optional

from src.database.models import UserCooldown

from .base import Base

logger = logging.getLogger(__name__)

class CooldownService(Base):

    async def get_user_cooldown(
        self,
        telegram_id: int,
        cooldown_name: str 
    ) -> Optional[UserCooldown]:
        
        logger.debug(f"Called method get_user_cooldown. Params: telegram_id={telegram_id}, cooldown_name={cooldown_name}")
        
        user_cooldown = await self.cooldown_repository\
            .get_user_cooldown(
                telegram_id=telegram_id, 
                cooldown_name=cooldown_name
            )
        
        logger.debug(f"User cooldown found: {user_cooldown is not None}. End process.")
        return user_cooldown
    
    async def get_active_cooldown(
        self,
        telegram_id: int,
        cooldown_name: str 
    ) -> Optional[UserCooldown]:
        
        logger.debug(f"Called method get_active_cooldown. Params: telegram_id={telegram_id}, cooldown_name={cooldown_name}")

        logger.debug("User cooldown_repository. Calling method get_active_cooldown.")
        
        user_cooldown = await self.cooldown_repository\
            .get_active_cooldown(
                telegram_id=telegram_id, 
                cooldown_name=cooldown_name
            )
        
        logger.debug(f"User cooldown equal {user_cooldown}. End process.")
        return user_cooldown

    async def get_cooldown(
        self,
        cooldown_name: str | None = None,
        cooldown_id: int | None = None
    ):
        
        logger.debug(f"Called method get_cooldown. Params: cooldown_name={cooldown_name}, cooldown_id={cooldown_id}")
        
        parameter = cooldown_name or cooldown_id

        if not parameter:
            logger.error("Arguments is invalid - both cooldown_name and cooldown_id are None")
            raise ValueError("Arguments is invalid")

        logger.debug(f"Searching cooldown with parameter: {parameter}")
        
        cooldown = await self.cooldown_repository\
            .get_cooldown(
                search_parameter=parameter
            )
        
        logger.debug(f"Cooldown found: {cooldown is not None}. End process.")
        return cooldown
    
    async def set_cooldown(
        self,
        telegram_id: int,
        cooldown_type: str
    ):
        
        logger.debug(f"Called method set_cooldown. Params: telegram_id={telegram_id}, cooldown_type={cooldown_type}")
        
        cooldown = await self.cooldown_repository.set_cooldown(
            user_id=telegram_id,
            cooldown_type=cooldown_type
        )
        
        logger.debug(f"Cooldown set successfully: {cooldown is not None}. End process.")
        return cooldown
    
    async def reset_cooldown(
        self,
        telegram_id: int,
        cooldown_type: str  
    ):
        logger.debug(f"Called method reset_cooldown. Params: telegram_id={telegram_id}, cooldown_type={cooldown_type}")
        
        user = await self.user_repository.get(search_parameter=telegram_id)

        if not user:
            logger.error(f"User not found in database for telegram_id: {telegram_id}")
            raise ValueError("User not found in database")
        
        logger.debug(f"User found: ID={user.id}. Proceeding to reset cooldown.")

        new_cooldown = await self.cooldown_repository.reset_cooldown(
            user_id=user.id,
            cooldown_type=cooldown_type
        )
        
        logger.debug(f"Cooldown reset successfully: {new_cooldown is not None}. End process.")
        return new_cooldown

    async def is_end_cooldown(
        self,
        telegram_id: int,
        cooldown_type: str
    ):
        logger.debug(f"Called method is_end_cooldown. Params: telegram_id={telegram_id}, cooldown_type={cooldown_type}")
        
        is_cooldown = await self.cooldown_repository\
            .is_cooldown_active(
                user_id=telegram_id,
                cooldown_type=cooldown_type
            )
        
        logger.debug(f"Cooldown active status: {is_cooldown}. End process.")
        return is_cooldown
    
__all__ = ["CooldownService"]