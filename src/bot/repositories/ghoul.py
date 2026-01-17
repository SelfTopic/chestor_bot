import logging
from typing import Any, List, Optional

from sqlalchemy import desc, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.types import KaguneType
from src.database.models import Ghoul

from .base import Base

logger = logging.getLogger(__name__)


class GhoulRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, telegram_id: int, **kwargs: Any) -> Ghoul:
        if "kagune_type_bit" in kwargs and isinstance(kwargs["kagune_type_bit"], int):
            kwargs["kagune_type_bit"] = self._validate_kagune_bit(
                kwargs["kagune_type_bit"]
            )

        values = {"telegram_id": telegram_id, **kwargs}

        update_dict = {
            k: v
            for k, v in values.items()
            if k not in ["id", "telegram_id", "created_at"]
        }

        if not update_dict:
            update_dict = {"updated_at": func.now()}

        ghoul = await self.session.scalar(
            insert(Ghoul)
            .values(**values)
            .on_conflict_do_update(index_elements=["telegram_id"], set_=update_dict)
            .returning(Ghoul)
        )

        if ghoul is None:
            logger.error(f"Ghoul ({telegram_id}) not found after upsert operation")
            raise Exception(f"Ghoul with telegram_id={telegram_id} not found")

        await self.session.refresh(ghoul)
        logger.debug(f"Upserted ghoul ({telegram_id})")
        return ghoul

    async def get(self, telegram_id: int) -> Optional[Ghoul]:
        ghoul = await self.session.scalar(
            select(Ghoul).where(Ghoul.telegram_id == telegram_id)
        )

        if ghoul:
            ghoul.kagune_type_bit = self._validate_kagune_bit(ghoul.kagune_type_bit)

        return ghoul

    async def get_by_id(self, id: int) -> Optional[Ghoul]:
        ghoul = await self.session.scalar(select(Ghoul).where(Ghoul.id == id))

        if ghoul:
            ghoul.kagune_type_bit = self._validate_kagune_bit(ghoul.kagune_type_bit)

        return ghoul

    async def exists(self, telegram_id: int) -> bool:
        exist = await self.session.scalar(
            select(exists(Ghoul.telegram_id)).where(Ghoul.telegram_id == telegram_id)
        )
        return bool(exist)

    async def update_kagune(
        self, telegram_id: int, new_kagune_bit: int, kagune_strength: int
    ) -> bool:
        validated_bit = self._validate_kagune_bit(new_kagune_bit)

        result = await self.session.execute(
            update(Ghoul)
            .where(Ghoul.telegram_id == telegram_id)
            .values(
                kagune_type_int=validated_bit,
                kagune_strength=kagune_strength,
                updated_at=func.now(),
            )
        )

        return result.rowcount > 0

    def _validate_kagune_bit(self, bit: int) -> int:
        if bit < 0:
            logger.warning(f"Negative kagune bitmask: {bit}. Resetting to 0.")
            return 0

        valid_bits = [k.value["bit"] for k in KaguneType]
        max_valid_bit = sum(valid_bits)

        if bit > max_valid_bit:
            logger.warning(
                f"Kagune bitmask {bit} exceeds max {max_valid_bit}. Trimming."
            )
            bit = max_valid_bit

        cleaned_bit = 0
        for kagune in KaguneType:
            if bit & kagune.value["bit"]:
                cleaned_bit |= kagune.value["bit"]

        unique_bits = sum({k.value["bit"] for k in self._calculate_kagune(cleaned_bit)})

        if unique_bits != cleaned_bit:
            logger.error(f"Duplicate bits detected: {bit} → {unique_bits}. Correcting.")
            return unique_bits

        return cleaned_bit

    async def get_top_snap(self, count: int) -> List[Ghoul]:
        stmt = select(Ghoul).order_by(desc(Ghoul.snap_count)).limit(count)

        execute = await self.session.scalars(stmt)

        return list(execute)

    def _calculate_kagune(self, bit: int) -> List[KaguneType]:
        result = []
        for kagune in KaguneType:
            if bit & kagune.value["bit"]:
                result.append(kagune)

        return result
