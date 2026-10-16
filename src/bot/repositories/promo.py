from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import PromoActivation, PromoCode
from .base import Base


class PromoRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        rewards: list[dict[str, Any]],
        activations_limit: int,
        expires_at: Optional[datetime],
        created_by: int,
    ) -> Optional[PromoCode]:
        stmt = (
            insert(PromoCode)
            .values(
                name=name,
                rewards=rewards,
                activations_limit=activations_limit,
                activations_used=0,
                expires_at=expires_at,
                created_by=created_by,
            )
            .on_conflict_do_nothing(
                index_elements=[PromoCode.name], index_where=PromoCode.deleted_at.is_(None)
            )
            .returning(PromoCode)
        )
        return (await self.session.scalars(stmt)).one_or_none()

    async def live_by_name(self, name: str) -> Optional[PromoCode]:
        return await self.session.scalar(
            select(PromoCode).where(PromoCode.name == name, PromoCode.deleted_at.is_(None))
        )

    async def latest_by_name(self, name: str) -> Optional[PromoCode]:
        return await self.session.scalar(
            select(PromoCode)
            .where(PromoCode.name == name)
            .order_by(PromoCode.deleted_at.is_not(None), PromoCode.deleted_at.desc())
            .limit(1)
        )

    async def by_id(self, promo_id: int) -> Optional[PromoCode]:
        # Удаление идёт UPDATE'ом мимо объекта в сессии: перечитываем строку, а не кэш.
        return await self.session.scalar(
            select(PromoCode)
            .where(PromoCode.id == promo_id)
            .execution_options(populate_existing=True)
        )

    async def count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(PromoCode)) or 0

    async def page(self, offset: int, limit: int) -> list[PromoCode]:
        rows = await self.session.scalars(
            select(PromoCode)
            .order_by(
                PromoCode.deleted_at.is_not(None), PromoCode.created_at.desc(), PromoCode.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
        return list(rows)

    async def delete(self, promo_id: int, deleted_at: datetime, deleted_by: int) -> bool:
        stmt = (
            update(PromoCode)
            .where(PromoCode.id == promo_id, PromoCode.deleted_at.is_(None))
            .values(deleted_at=deleted_at, deleted_by=deleted_by)
            .returning(PromoCode.id)
        )
        return await self.session.scalar(stmt) is not None

    async def record_activation(self, promo_id: int, telegram_id: int) -> bool:
        stmt = (
            insert(PromoActivation)
            .values(promo_id=promo_id, telegram_id=telegram_id)
            .on_conflict_do_nothing()
            .returning(PromoActivation.promo_id)
        )
        return await self.session.scalar(stmt) is not None

    # Счётчик и лимит сравниваются в одном UPDATE: одновременные активации не превысят лимит.
    async def claim_activation(self, promo_id: int) -> bool:
        stmt = (
            update(PromoCode)
            .where(
                PromoCode.id == promo_id,
                PromoCode.activations_used < PromoCode.activations_limit,
            )
            .values(activations_used=PromoCode.activations_used + 1)
            .returning(PromoCode.id)
        )
        return await self.session.scalar(stmt) is not None
