import logging
import time
from typing import Optional, Union

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Cooldown, UserCooldown

from .base import Base

logger = logging.getLogger(__name__)

class UserCooldownRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository with an async database session.
        
        Args:
            session (AsyncSession): Async database session
        """
        self.session = session
        logger.debug("UserCooldownRepository initialized")

    async def get_user_cooldown(
        self,
        telegram_id: int,
        cooldown_name: str 
    ) -> Optional[UserCooldown]:
        
        cooldown = await self.get_cooldown(
            search_parameter=cooldown_name
        )

        if not cooldown:
            logger.debug("Cooldown not found")
            raise ValueError(f"Cooldown name {cooldown_name} not found")

        stmt = select(UserCooldown)\
            .filter(
                UserCooldown.user_id == telegram_id,
                UserCooldown.cooldown_id == cooldown.id
            )
        
        user_coolodwn = await self.session.scalar(stmt)

        return user_coolodwn
    

    async def set_cooldown(
        self, 
        user_id: int, 
        cooldown_type: str
    ) -> UserCooldown:
        """
        Set or update cooldown for user
        
        Args:
            user_id: ID of user
            cooldown_type: Type of cooldown (e.g. 'snap', 'raise_kagune')
        """
        cooldown = await self.session.execute(
            select(Cooldown)
            .filter(
                Cooldown.name == cooldown_type
            )
        )
        cooldown = cooldown.scalar_one_or_none()
        
        if not cooldown:
            logger.error(f"Cooldown type '{cooldown_type}' not found")
            raise ValueError(f"Invalid cooldown type: {cooldown_type}")
        
        end_at = time.time() + cooldown.duration
        

        user_cooldown = await self.session.scalar(
    
            insert(UserCooldown)
            .values(
                user_id=user_id,
                cooldown_id=cooldown.id,
                end_at=end_at
            )
            .on_conflict_do_update(
                index_elements=["user_id", "cooldown_id"],
                set_={
                    "end_at": end_at
                }
            )
            .returning(UserCooldown)

        )

        if not user_cooldown:
            logger.error("User cooldown is not found")
            raise ValueError("User cooldown is not found")

        logger.debug(f"Cooldown '{cooldown_type}' set for user {user_id} until {end_at}")

        return user_cooldown

    async def is_cooldown_active(
        self, 
        user_id: int, 
        cooldown_type: str
    ):
        """
        Check if cooldown is active for user
        
        Args:
            user_id: ID of user
            cooldown_type: Type of cooldown
            
        Returns:
            bool: True if cooldown is active
        """
        stmt = select(UserCooldown).join(
            Cooldown, 
            onclause=UserCooldown.cooldown_id == Cooldown.id 
            ).where(
            and_(
                UserCooldown.user_id == user_id,
                Cooldown.name == cooldown_type,
                UserCooldown.end_at > time.time()
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_cooldown_end(
        self, 
        user_id: int, 
        cooldown_type: str
    ) -> int | None:
        """
        Get cooldown end time if active
        
        Args:
            user_id: ID of user
            cooldown_type: Type of cooldown
            
        Returns:
            datetime | None: End time if active, else None
        """
        stmt = select(UserCooldown.end_at).join(Cooldown).where(
            and_(
                UserCooldown.user_id == user_id,
                Cooldown.name == cooldown_type,
                UserCooldown.end_at > func.now()
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_cooldown(
        self,
        search_parameter: Union[int, str]         
    ):
        parameter = Cooldown.name 

        if isinstance(search_parameter, int):
            parameter = Cooldown.id

        cooldown = await self.session.scalar(
            select(Cooldown)
            .filter(
                parameter == search_parameter  
            )
        )   

        return cooldown

    async def reset_cooldown(
        self, 
        user_id: int, 
        cooldown_type: str
    ):
        """
        Reset cooldown for user
        
        Args:
            user_id: ID of user
            cooldown_type: Type of cooldown
        """
        cooldown = await self.session.scalar(
            select(Cooldown).filter(Cooldown.name == cooldown_type)
        )
        
        if not cooldown:
            logger.error(f"Cooldown type '{cooldown_type}' not found")
            return

        stmt = update(UserCooldown)\
            .values(
                end_at=int(time.time()) + cooldown.duration    
            )\
            .filter(
                UserCooldown.user_id == user_id,
                UserCooldown.cooldown_id == cooldown.id
            )\
            .returning(UserCooldown)
    

        logger.debug(f"Cooldown '{cooldown_type}' reset for user {user_id}")
        return await self.session.scalar(stmt)

    async def get_active_cooldown(self, telegram_id: int, cooldown_name: str):
        """
        Get active cooldown for specific type
        """
        stmt = select(UserCooldown).join(
            Cooldown, 
            UserCooldown.cooldown_id == Cooldown.id
        ).where(
            and_(
                UserCooldown.user_id == telegram_id,
                Cooldown.name == cooldown_name, 
                UserCooldown.end_at > time.time()
            )
        )
        result = await self.session.scalar(stmt)
        return result

    async def cleanup_expired_cooldowns(self) -> int:
        """
        Delete all expired cooldown records
        
        Returns:
            int: Number of deleted records
        """
        stmt = delete(UserCooldown)\
            .where(UserCooldown.end_at <= func.now())
        
        result = await self.session.execute(stmt)

        deleted = result.rowcount
        logger.info(f"Cleaned up {deleted} expired cooldowns")
        return deleted

    async def add_cooldown_type(
        self, 
        cooldown_type: str, 
        duration: int
    ) -> Cooldown:
        """
        Add new cooldown type to the system
        
        Args:
            cooldown_type: Unique cooldown type name
            duration: Cooldown duration
            
        Returns:
            Cooldown: Created cooldown object
        """

        cooldown = await self.session.scalar(
            insert(Cooldown)
            .values(
                name=cooldown_type, 
                duration=duration
            )   
            .returning(Cooldown)
        )

        if not cooldown:

            raise
        logger.info(f"Added new cooldown type: {cooldown_type} ({duration})")
        return cooldown