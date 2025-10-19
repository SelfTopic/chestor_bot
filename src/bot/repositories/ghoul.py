from .base import Base

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, exists, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Ghoul
from src.bot.types import KaguneType

from typing import Optional, Union, List, Dict, Any

import logging

logger = logging.getLogger(__name__)


class GhoulRepository(Base):
    """
    Repository class for managing Ghoul entities in the database.
    Provides CRUD operations with additional validation for kagune bitmasks.
    
    Attributes:
        session (AsyncSession): Async database session
    """
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository with an async database session.
        
        Args:
            session (AsyncSession): Async database session
        """
        self.session = session

    async def upsert(
        self,
        telegram_id: int,
        **kwargs: Any
    ) -> Ghoul:
        """
        Insert or update a Ghoul record based on telegram_id.
        
        Automatically validates and corrects kagune_type_int if provided.
        Updates 'updated_at' timestamp on conflict.
        
        Args:
            telegram_id (int): Unique Telegram identifier
            **kwargs: Additional ghoul attributes to set/update
            
        Returns:
            Ghoul: Created or updated Ghoul instance
            
        Raises:
            Exception: If record not found after upsert operation
        """
        # Validate kagune bitmask if provided
        if 'kagune_type_bit' in kwargs and isinstance(kwargs['kagune_type_bit'], int):
            kwargs['kagune_type_bit'] = self._validate_kagune_bit(kwargs['kagune_type_bit']) # type: ignore

        
        values = {"telegram_id": telegram_id, **kwargs}
        
        # Build update dictionary (exclude immutable fields)
        update_dict = {k: v for k, v in values.items() 
                      if k not in ['id', 'telegram_id', 'created_at']}
        
        # Ensure we update timestamp even if no other fields change
        if not update_dict:
            update_dict = {'updated_at': func.now()}

        # Execute upsert operation
        ghoul = await self.session.scalar(
            insert(Ghoul)
            .values(**values)
            .on_conflict_do_update(
                index_elements=['telegram_id'],
                set_=update_dict
            )
            .returning(Ghoul)
        )

        if ghoul is None:
            logger.error(f"Ghoul ({telegram_id}) not found after upsert operation")
            raise Exception(f'Ghoul with telegram_id={telegram_id} not found')
        
        await self.session.refresh(ghoul)
        logger.debug(f"Upserted ghoul ({telegram_id})")
        return ghoul

    async def get(
        self, 
        telegram_id: int
    ) -> Optional[Ghoul]:
        """
        Retrieve a Ghoul by identifier.
        
        Currently only supports integer lookups (telegram_id). String lookups 
        return None since Ghoul model doesn't have username field.
        
        Args:
            search_parameter (Union[str, int]): Search value
            
        Returns:
            Optional[Ghoul]: Found Ghoul or None
        """
        ghoul = await self.session.scalar(
            select(Ghoul)
            .where(Ghoul.telegram_id == telegram_id)
        )

        if ghoul:
            # Ensure kagune bitmask is valid after loading
            ghoul.kagune_type_bit = self._validate_kagune_bit(ghoul.kagune_type_bit)
        
        return ghoul

    async def get_by_id(self, id: int) -> Optional[Ghoul]:
        """
        Retrieve a Ghoul by primary database ID.
        
        Args:
            id (int): Primary key identifier
            
        Returns:
            Optional[Ghoul]: Found Ghoul or None
        """
        ghoul = await self.session.scalar(
            select(Ghoul)
            .where(Ghoul.id == id)
        )
        
        if ghoul:
            ghoul.kagune_type_bit = self._validate_kagune_bit(ghoul.kagune_type_bit)
        
        return ghoul

    async def exists(self, telegram_id: int) -> bool:
        """
        Check if a Ghoul exists with given telegram_id.
        
        Args:
            telegram_id (int): Telegram identifier to check
            
        Returns:
            bool: True if exists, False otherwise
        """
        exist = await self.session.scalar(
            select(exists(Ghoul.telegram_id))
            .where(Ghoul.telegram_id == telegram_id)
        )
        return bool(exist)

    async def update_kagune(
        self,
        telegram_id: int,
        new_kagune_bit: int,
        kagune_strength: int
    ) -> bool:
        """
        Safely update a Ghoul's kagune configuration.
        
        Validates bitmask before updating and sets updated_at timestamp.
        
        Args:
            telegram_id (int): Target Ghoul's identifier
            new_kagune_bit (int): New kagune bitmask
            kagune_strength (int): New kagune strength value
            
        Returns:
            bool: True if update succeeded, False otherwise
        """
        
        validated_bit = self._validate_kagune_bit(new_kagune_bit)
        
        result = await self.session.execute(
            update(Ghoul)
            .where(Ghoul.telegram_id == telegram_id)
            .values(
                kagune_type_int=validated_bit,
                kagune_strength=kagune_strength,
                updated_at=func.now()
            )
        )
        
        return result.rowcount > 0

    def _validate_kagune_bit(self, bit: int) -> int:
        """
        Validate and correct kagune bitmask value.
        
        Performs:
        - Negative value correction
        - Maximum value enforcement
        - Invalid bit filtering
        - Duplicate bit removal
        
        Args:
            bit (int): Original bitmask value
            
        Returns:
            int: Validated and corrected bitmask
        """
        # Handle negative values
        if bit < 0:
            logger.warning(f"Negative kagune bitmask: {bit}. Resetting to 0.")
            return 0
        
        # Calculate maximum valid bitmask
        valid_bits = [k.value["bit"] for k in KaguneType]
        max_valid_bit = sum(valid_bits)
        
        # Enforce maximum value
        if bit > max_valid_bit:
            logger.warning(f"Kagune bitmask {bit} exceeds max {max_valid_bit}. Trimming.")
            bit = max_valid_bit
        
        # Filter invalid bits
        cleaned_bit = 0
        for kagune in KaguneType:
            if bit & kagune.value["bit"]:
                cleaned_bit |= kagune.value["bit"]
        
        # Remove duplicate bits (shouldn't occur but protects against data corruption)
        unique_bits = sum({k.value["bit"] for k in self._calculate_kagune(cleaned_bit)})
        
        if unique_bits != cleaned_bit:
            logger.error(f"Duplicate bits detected: {bit} → {unique_bits}. Correcting.")
            return unique_bits
        
        return cleaned_bit

    def _calculate_kagune(self, bit: int) -> List[KaguneType]:
        """
        Calculate KaguneType list from bitmask.
        
        Args:
            bit (int): Validated kagune bitmask
            
        Returns:
            List[KaguneType]: Kagune types represented in bitmask
        """
        result = []
        for kagune in KaguneType:
            if bit & kagune.value["bit"]:
                result.append(kagune)
                
        return result