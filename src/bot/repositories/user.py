from .base import Base 
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from ...database.models import User
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

class UserRepository(Base):
    """
    Repository class for handling database operations related to User entities.
    
    Provides CRUD operations with PostgreSQL-specific optimizations like UPSERT.
    """
    
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the UserRepository with a database session.
        
        Args:
            session: Async SQLAlchemy session for database operations
        """
        self.session = session
        logger.debug("UserRepository initialized with database session")

    async def upsert(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
    ) -> User:
        """
        Create or update a User record using PostgreSQL UPSERT functionality.
        
        Performs atomic "INSERT OR UPDATE" operation to ensure data consistency.
        Refreshes the object state after database operation.
        
        Args:
            telegram_id: Unique Telegram user identifier
            first_name: User's first name
            last_name: User's last name (optional)
            username: Telegram username (optional)
            
        Returns:
            User: Created or updated User object
            
        Raises:
            Exception: If user record mysteriously disappears after insertion
        """
        logger.info(f"Upserting user (Telegram ID: {telegram_id})")
        logger.debug(f"User data: {first_name} {last_name} (@{username})")
        
        # Construct and execute UPSERT statement
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
        
        # Handle potential insertion anomaly
        if user is None:
            error_msg = f"User ({telegram_id}) not found after UPSERT operation"
            logger.critical(error_msg)
            raise Exception(error_msg)
            
        # Refresh object state to ensure consistency
        await self.session.refresh(user)
        logger.info(f"User record {'created' if user.id is None else 'updated'}: ID {user.id}")
        return user
    
    async def get(self, search_parameter: Union[str, int]) -> Optional[User]:
        """
        Retrieve a user by Telegram ID or username.
        
        Automatically determines search method based on parameter type:
        - Integer: Search by telegram_id
        - String: Search by username
        
        Args:
            search_parameter: Either Telegram ID (int) or username (str)
            
        Returns:
            User object if found, None otherwise
        """
        logger.debug(f"Searching user by: {search_parameter} ({type(search_parameter).__name__})")
        
        # Dynamic column selection based on input type
        if isinstance(search_parameter, int):
            search_column = User.telegram_id
            search_type = "Telegram ID"
        else:
            search_column = User.username
            search_type = "username"
            logger.debug("String parameter detected, searching by username")

        # Execute database query
        user = await self.session.scalar(
            select(User).where(search_column == search_parameter)
        )
        
        if not user:
            logger.info(f"User not found by {search_type}: {search_parameter}")
            return None
            
        logger.debug(f"User found: ID {user.id}")
        return user
    
    async def exists(self, telegram_id: int) -> bool:
        """
        Check if a user exists in the database by Telegram ID.
        
        Optimized existence check using SQL EXISTS clause for performance.
        
        Args:
            telegram_id: Telegram user identifier
            
        Returns:
            True if user exists, False otherwise
        """
        logger.debug(f"Checking existence of user (Telegram ID: {telegram_id})")
        
        # Use SQL EXISTS for efficient existence check
        exists_query = await self.session.scalar(
            select(exists().where(User.telegram_id == telegram_id))
        )

        if not exists_query:
            raise ValueError("Exists query is not found (anomaly)")
        
        logger.info(f"User {telegram_id} {'exists' if exists_query else 'does not exist'}")
        return bool(exists_query)