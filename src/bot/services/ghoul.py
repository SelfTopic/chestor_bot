from .base import Base 
from src.database.models import Ghoul
from aiogram.types import Message
from ..types import RegisterGhoulType, KaguneType
from ..utils import calculate_kagune
from typing import Union, Optional, Any
import random, logging 

logger = logging.getLogger(__name__)


class GhoulService(Base):
    """Service class for managing business logic related to Ghoul entities."""

    async def get(self, find_by: Union[Message, int]) -> Optional[Ghoul]:
        """
        Retrieve a Ghoul entity using different identifier types.

        Supports:
        - Telegram Message object (extracts user ID)
        - Telegram user ID (integer)
        - Custom ghoul ID (small integer < 666000)

        Args:
            find_by: Search parameter (Message object or integer ID)

        Returns:
            Ghoul instance if found, None otherwise

        Raises:
            ValueError: For unsupported parameter types
        """
        logger.debug(f"Retrieving ghoul using identifier: {find_by}")
        search_parameter = find_by

        # Extract user ID from Message object
        if isinstance(find_by, Message):
            logger.debug("Received Message object, extracting user ID")
            if not find_by.from_user:
                logger.warning("Message has no from_user attribute")
                return None
            search_parameter = find_by.from_user.id

        # Process integer identifiers
        if isinstance(search_parameter, int):
            # Standard Telegram user ID
            if search_parameter > 666000:
                logger.debug(f"Looking up by Telegram ID: {search_parameter}")
                ghoul = await self.ghoul_repository.get(search_parameter)
            # Custom ghoul ID
            else:
                logger.debug(f"Looking up by custom ID: {search_parameter}")
                ghoul = await self.ghoul_repository.get_by_id(search_parameter)
            return ghoul

        logger.error(f"Invalid parameter type: {type(search_parameter)}")
        raise ValueError(f"Invalid type parameter: {type(search_parameter)}. Valid types: Message, int")
    

    async def snap_finger(self, telegram_id: int) -> Ghoul:

        ghoul = await self.get(telegram_id)

        if not ghoul:
            raise ValueError("Ghoul not found")
        
        ghoul_updated = await self.ghoul_repository.upsert(
            telegram_id=telegram_id,
            snap_count=ghoul.snap_count + 1
        )

        return ghoul_updated



    async def upsert(self, telegram_id: int, **kw: Any) -> Ghoul:
        """
        Create or update a Ghoul entity.

        Args:
            telegram_id: Unique Telegram user identifier
            **kw: Additional attributes for creation/update

        Returns:
            Created/updated Ghoul entity
        """
        logger.info(f"Upserting ghoul with Telegram ID: {telegram_id}")
        logger.debug(f"Additional parameters: {kw}")
        ghoul = await self.ghoul_repository.upsert(
            telegram_id=telegram_id, 
            **kw
        )
        logger.info(f"Ghoul created/updated ID {ghoul.id}")
        return ghoul

    async def register(self, telegram_id: int) -> RegisterGhoulType:
        """
        Register a new ghoul in the system.

        Args:
            telegram_id: Unique Telegram user identifier

        Returns:
            RegisterGhoulType: Registration status object
        """
        logger.info(f"Starting registration for Telegram ID: {telegram_id}")
        ghoul = await self.get(find_by=telegram_id)

        # Handle existing ghoul
        if ghoul:
            logger.warning(f"Registration failed: User {telegram_id} already exists")
            return RegisterGhoulType(ok=False, is_found=True)

        # Create new ghoul with random kagune
        logger.debug("Generating initial kagune type")
        first_kagune = self._first_kagune()
        logger.info(f"Assigning kagune type: {calculate_kagune(first_kagune)[0].name}")

        ghoul = await self.upsert(
            telegram_id=telegram_id,
            kagune_type_bit=first_kagune
        )
        logger.info(f"Successfully registered new ghoul: ID {ghoul.id}")
        return RegisterGhoulType(
            ok=True,
            is_found=True,
            ghoul=ghoul    
        )

    def _first_kagune(self) -> int:
        """
        Generate random initial kagune type for new ghouls.

        Returns:
            Integer bitmask representing kagune type
        """
        # Get all possible kagune bit values from enum
        bits = [kagune.value["bit"] for kagune in KaguneType]
        logger.debug(f"Available kagune bits: {bits}")
        
        selected = random.choice(bits)
        logger.debug(f"Selected kagune bit: {selected}")
        return selected
    
__all__ = ["GhoulService"]