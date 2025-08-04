from .base import Base 

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import User
from typing import Optional, Union

import logging

logger = logging.getLogger(__name__)

class UserRepository(Base):

    session: AsyncSession

    def __init__(
        self,
        session: AsyncSession
    ) -> None: 
        
        # Set session 
        self.session = session 

    async def upsert(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
    ) -> User:
        user = await self.session.scalar(
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
                },
            )
            .returning(User)
        )

        if user is None:
            logger.error(f"After adding to the database, the user ({telegram_id}) was not found in it")
            raise Exception(
                f'User with telegram_id=`{telegram_id}` not found'
            )
        await self.session.refresh(user)  # Updating object from database 

        logger.debug(f"Added/Updated user ({telegram_id}) in database")
        return user
    
    async def get(
        self,
        search_parameter: Union[str, int]
    ) -> Optional[User]:
        
        # Setting column for searching
        search_column = User.telegram_id

        if isinstance(search_parameter, str):
            search_column = User.username # Find by username if argument str type

        user = await self.session.scalar(
            select(User)
            .filter(search_column == search_parameter)
        )

        if not user:
            logger.debug(f"User ({search_parameter}) not found in database")

        return user
    
    async def exists(self, telegram_id: int) -> bool:

        exist = await self.session.scalar(
            select(exists(User.telegram_id)).where(User.telegram_id == telegram_id)
        )

        if not exist: 
            return False 
        
        return exist