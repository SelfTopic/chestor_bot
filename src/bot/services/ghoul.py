import logging
import random
from typing import Any, List, Optional, Union

from aiogram.types import Message

from src.database.models import Ghoul

from ..game_configs import KAGUNE_CONFIG
from ..types import KaguneType, Race, RegisterGhoulType
from .base import Base

logger = logging.getLogger(__name__)


class GhoulService(Base):
    async def get(self, find_by: Union[Message, int]) -> Optional[Ghoul]:
        logger.debug(
            f"Called method get. Params: find_by={find_by if not isinstance(find_by, Message) else 'Message'}"
        )

        search_parameter = find_by

        if isinstance(find_by, Message):
            logger.debug("Received Message object, extracting user ID")
            if not find_by.from_user:
                logger.warning("Message has no from_user attribute")
                return None
            search_parameter = find_by.from_user.id

        if isinstance(search_parameter, int):
            if search_parameter > 666000:
                logger.debug(f"Looking up by Telegram ID: {search_parameter}")
                ghoul = await self.ghoul_repository.get(search_parameter)
            else:
                logger.debug(f"Looking up by custom ID: {search_parameter}")
                ghoul = await self.ghoul_repository.get_by_id(search_parameter)

            logger.debug(f"Ghoul found: {ghoul is not None}")
            return ghoul

        logger.error(f"Invalid parameter type: {type(search_parameter)}")
        raise ValueError(f"Invalid type parameter: {type(search_parameter)}")

    async def snap_finger(self, telegram_id: int) -> Ghoul:
        logger.debug(f"Called method snap_finger. Params: telegram_id={telegram_id}")

        ghoul = await self.get(telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for snap_finger operation")
            raise ValueError("Ghoul not found")

        logger.debug(f"Current snap count: {ghoul.snap_count}. Incrementing...")

        ghoul_updated = await self.ghoul_repository.upsert(
            telegram_id=telegram_id, snap_count=ghoul.snap_count + 1
        )

        logger.debug(
            f"Snap count updated successfully. New count: {ghoul_updated.snap_count}"
        )
        return ghoul_updated

    async def coffee(self, telegram_id: int, change: int = 1) -> Ghoul:
        logger.debug(
            f"Called method coffee. Params: telegram_id={telegram_id}, change={change}"
        )

        ghoul = await self.get(find_by=telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for coffee operation")
            raise ValueError("Ghoul not found")

        ghoul = await self.ghoul_repository.upsert(
            telegram_id=telegram_id, coffee_count=ghoul.coffee_count + change
        )

        return ghoul

    async def upgrade_kagune(self, telegram_id: int, change: int = 1) -> Ghoul:
        logger.debug(
            f"Called method upsert. Params: telegram_id={telegram_id}, change={change}"
        )

        ghoul = await self.get(find_by=telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for upgarde_kagune operation")
            raise ValueError("Ghoul not found")

        ghoul = await self.ghoul_repository.upsert(
            telegram_id=telegram_id, kagune_strength=ghoul.kagune_strength + change
        )

        return ghoul

    async def upsert(self, telegram_id: int, **kw: Any) -> Ghoul:
        logger.debug(
            f"Called method upsert. Params: telegram_id={telegram_id}, kwargs={kw}"
        )

        ghoul = await self.ghoul_repository.upsert(telegram_id=telegram_id, **kw)

        logger.debug(f"Ghoul upserted successfully. ID: {ghoul.id}")
        return ghoul

    async def register(self, telegram_id: int) -> RegisterGhoulType:
        logger.debug(f"Called method register. Params: telegram_id={telegram_id}")

        ghoul = await self.get(find_by=telegram_id)

        if ghoul:
            logger.warning(f"Registration failed: User {telegram_id} already exists")
            return RegisterGhoulType(ok=False, is_found=True)

        logger.debug("Generating initial kagune type for new ghoul")
        first_kagune = self._first_kagune()

        ghoul = await self.upsert(telegram_id=telegram_id, kagune_type_bit=first_kagune)

        await self.user_repository.change_data(
            telegram_id=telegram_id, race_bit=Race.GHOUL.value["bit"]
        )

        logger.info(f"Successfully registered new ghoul: ID {ghoul.id}")
        return RegisterGhoulType(ok=True, is_found=True, ghoul=ghoul)

    async def get_top_snap(self, count=20) -> List[Ghoul]:
        return await self.ghoul_repository.get_top_snap(count)

    def _first_kagune(self) -> int:
        logger.debug("Called method _first_kagune")

        bits = [kagune.value["bit"] for kagune in KaguneType]
        logger.debug(f"Available kagune bits: {bits}")

        selected = random.choice(bits)
        logger.debug(f"Selected kagune bit: {selected}")
        return selected

    def calculate_price_upgrade_kagune(self, kagune_strength: int) -> int:
        return int(
            KAGUNE_CONFIG.base_price * (kagune_strength**KAGUNE_CONFIG.exponent)
            + kagune_strength * KAGUNE_CONFIG.linear_multiplier
        )

    def calculate_power(self, ghoul: Ghoul) -> int:
        logger.debug(f"Called method calculate_power. Ghoul ID: {ghoul.id}")
        power = (
            ghoul.strength
            + ghoul.dexterity
            + ghoul.speed
            + ghoul.max_health
            + ghoul.regeneration
            + ghoul.kagune_strength
        )
        logger.debug(f"Calculated power: {power}")
        return power

    def get_danger_rank(self, power: int) -> str:
        logger.debug(f"Called method get_danger_rank. Power: {power}")
        if power < 500:
            return "F"
        elif power < 1000:
            return "D"
        elif power < 1500:
            return "C"
        elif power < 2000:
            return "B"
        elif power < 3500:
            return "A"
        elif power < 5000:
            return "S"
        elif power < 7500:
            return "SS"
        elif power < 10000:
            return "SSS"
        else:
            return "SSS+"


__all__ = ["GhoulService"]
