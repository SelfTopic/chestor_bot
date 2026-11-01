import logging
from typing import Any, List, Literal, Optional

from sqlalchemy import desc, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.types import KaguneType
from src.database.models import Ghoul

from .base import Base
from .chat_participant import in_chat

logger = logging.getLogger(__name__)

TopKind = Literal["snap", "power", "kagune"]


def _total_kagune_strength() -> Any:
    return (
        func.coalesce(Ghoul.kagune_strength_ukaku, 0)
        + func.coalesce(Ghoul.kagune_strength_koukaku, 0)
        + func.coalesce(Ghoul.kagune_strength_rinkaku, 0)
        + func.coalesce(Ghoul.kagune_strength_bikaku, 0)
    )


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

    async def increment_fields(self, telegram_id: int, **deltas: int) -> Optional[Ghoul]:
        if not deltas:
            raise ValueError("No fields to increment")

        values = {
            field: getattr(Ghoul, field) + delta for field, delta in deltas.items()
        }

        stmt = (
            update(Ghoul)
            .where(Ghoul.telegram_id == telegram_id)
            .values(**values)
            .returning(Ghoul)
        )

        return await self.session.scalar(stmt)

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

    def _validate_kagune_bit(self, bit: int) -> int:
        if bit is None:
            return 0

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

    # Список топа и место игрока в нём считаются одним порядком: место совпадает с номером
    # строки, поэтому у равных значений есть последний ключ — id гуля.
    def _ranking(
        self, kind: TopKind, chat_id: Optional[int], kagune_type: Optional[KaguneType]
    ) -> tuple[Any, list[Any]]:
        stmt = select(Ghoul).where(Ghoul.is_dead.is_(False))
        if chat_id is not None:
            stmt = stmt.where(in_chat(chat_id, Ghoul.telegram_id))
        if kind == "snap":
            value = Ghoul.snap_count
        elif kind == "power":
            value = (
                Ghoul.strength
                + Ghoul.dexterity
                + Ghoul.speed
                + Ghoul.max_health
                + Ghoul.regeneration
                + _total_kagune_strength()
            )
        elif kagune_type is None:
            value = _total_kagune_strength()
        else:
            # В топ по типу попадают только те, у кого тип открыт (NULL не считается нулём).
            value = getattr(Ghoul, kagune_type.value["strength_column"])
            stmt = stmt.where(value.isnot(None))
        return stmt, [desc(value), Ghoul.id]

    async def top(
        self,
        kind: TopKind,
        count: int,
        chat_id: Optional[int] = None,
        kagune_type: Optional[KaguneType] = None,
    ) -> List[Ghoul]:
        stmt, order = self._ranking(kind, chat_id, kagune_type)
        return list(await self.session.scalars(stmt.order_by(*order).limit(count)))

    async def place(
        self,
        kind: TopKind,
        telegram_id: int,
        chat_id: Optional[int] = None,
        kagune_type: Optional[KaguneType] = None,
    ) -> Optional[int]:
        stmt, order = self._ranking(kind, chat_id, kagune_type)
        ranked = stmt.with_only_columns(
            Ghoul.telegram_id, func.row_number().over(order_by=order).label("place")
        ).subquery()
        return await self.session.scalar(
            select(ranked.c.place).where(ranked.c.telegram_id == telegram_id)
        )

    def _calculate_kagune(self, bit: int) -> List[KaguneType]:
        result = []
        for kagune in KaguneType:
            if bit & kagune.value["bit"]:
                result.append(kagune)

        return result

    async def delete(self, telegram_id: int) -> bool:
        ghoul = await self.get(telegram_id)
        if not ghoul:
            return False
        await self.session.delete(ghoul)
        return True
