from .base import Base 
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from ...database.models import User
from typing import Optional, Union, Any
import logging

logger = logging.getLogger(__name__)

class UserRepository(Base):
    
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        logger.debug("UserRepository initialized with database session")
        self.session = session

    async def upsert(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
    ) -> User:
        logger.debug(f"Called method upsert. Params: telegram_id={telegram_id}, first_name={first_name}, last_name={last_name}, username={username}")
        
        upsert_stmt = (
            insert(User)
            .values(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
            )
            .on_conflict_do_update(
                index_elements=['telegram_id'],
                set_={
                    'first_name': first_name,
                    'last_name': last_name,
                    'username': username,
                }
            )
            .returning(User)
        )
        
        user = await self.session.scalar(upsert_stmt)
        
        if user is None:
            logger.error(f"User ({telegram_id}) not found after UPSERT operation")
            raise Exception(f"User ({telegram_id}) not found after UPSERT operation")
            
        await self.session.refresh(user)
        logger.debug(f"User record upserted successfully: ID {user.id}")
        return user
    
    async def get(self, search_parameter: Union[str, int]) -> Optional[User]:
        logger.debug(f"Called method get. Search parameter: {search_parameter}")
        
        if isinstance(search_parameter, int):
            search_column = User.telegram_id
            search_type = "Telegram ID"
        else:
            search_column = User.username
            search_type = "username"

        user = await self.session.scalar(
            select(User).where(search_column == search_parameter)
        )
        
        if not user:
            logger.debug(f"User not found by {search_type}: {search_parameter}")
            return None
            
        logger.debug(f"User found: ID {user.id}")
        return user
    
    async def exists(self, telegram_id: int) -> bool:
        logger.debug(f"Called method exists. Params: telegram_id={telegram_id}")
        
        exists_query = await self.session.scalar(
            select(exists().where(User.telegram_id == telegram_id))
        )

        if not exists_query:
            logger.error("Exists query returned None (anomaly)")
            raise ValueError("Exists query is not found (anomaly)")
        
        logger.debug(f"User existence check result: {bool(exists_query)}")
        return bool(exists_query)
    
    async def change_data(
        self, 
        telegram_id: int, 
        **kw: Any
    ) -> User:
        logger.debug(f"Called method change_data. Params: telegram_id={telegram_id}. Kwargs={kw}")

        exists = await self.exists(telegram_id=telegram_id)

        if not exists:
            logger.error("Cannot change data to nouser")
            raise ValueError("Cannot change data to nouser")

        stmt = insert(User)\
            .values(
                telegram_id=telegram_id,
                first_name="Mock data"
            )\
            .on_conflict_do_update(
                index_elements=['telegram_id'],
                set_=kw    
            ).returning(User)
        
        user = await self.session.scalar(stmt)

        if not user:
            logger.error("Cannot change data to nouser")
            raise ValueError("Cannot change data to nouser")

        return user

    
__all__ = ["UserRepository"]