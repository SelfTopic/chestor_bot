from typing import Any, Optional

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DuelSession

from .base import Base


class DuelSessionRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, chat_id: int, initiator_telegram_id: int, target_telegram_id: int
    ) -> DuelSession:
        stmt = (
            insert(DuelSession)
            .values(
                chat_id=chat_id,
                initiator_telegram_id=initiator_telegram_id,
                target_telegram_id=target_telegram_id,
            )
            .returning(DuelSession)
        )
        session = await self.session.scalar(stmt)
        if not session:
            raise ValueError("Не удалось создать DuelSession")
        return session

    async def atomic_update(
        self, duel_id: int, expected_stage: str, **fields: Any
    ) -> Optional[DuelSession]:
        """UPDATE ... WHERE id=duel_id AND stage=expected_stage RETURNING -
        единственный примитив для ЛЮБОГО перехода состояния дуэли (см.
        докстринг `DuelSession`). `None` - гонка проиграна: сессия уже не
        в `expected_stage` (либо нажатие кнопки, либо таймаут её успели
        увести раньше) - вызывающий код в этом случае просто ничего не
        делает, это НЕ ошибка."""

        stmt = (
            update(DuelSession)
            .where(DuelSession.id == duel_id, DuelSession.stage == expected_stage)
            .values(**fields)
            .returning(DuelSession)
        )
        return await self.session.scalar(stmt)

    async def get(self, duel_id: int) -> Optional[DuelSession]:
        return await self.session.scalar(select(DuelSession).where(DuelSession.id == duel_id))

    async def find_active_for(self, telegram_id: int) -> Optional[DuelSession]:
        return await self.session.scalar(
            select(DuelSession).where(
                DuelSession.stage != "done",
                (DuelSession.initiator_telegram_id == telegram_id)
                | (DuelSession.target_telegram_id == telegram_id),
            )
        )


__all__ = ["DuelSessionRepository"]
