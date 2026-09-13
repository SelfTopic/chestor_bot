import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ChatParticipant
from .base import Base

logger = logging.getLogger(__name__)


class ChatParticipantRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, chat_id: int, telegram_id: int) -> None:
        """Отмечает "этот юзер писал в этом чате" - вызывается на КАЖДОЕ
        сообщение в группе (см. SyncEntitiesService.sync), поэтому только
        INSERT ... ON CONFLICT DO UPDATE (обновляет last_seen_at), без
        отдельного чтения перед записью."""

        stmt = (
            insert(ChatParticipant)
            .values(chat_id=chat_id, telegram_id=telegram_id)
            .on_conflict_do_update(
                index_elements=["chat_id", "telegram_id"],
                set_={"last_seen_at": func.now()},
            )
        )
        await self.session.execute(stmt)

    async def get_random_participant(self, chat_id: int) -> Optional[int]:
        """Возвращает telegram_id случайного участника этого чата (среди
        тех, кто хоть раз написал - см. докстринг модели), или None, если
        для чата ещё никого не записано."""

        stmt = (
            select(ChatParticipant.telegram_id)
            .where(ChatParticipant.chat_id == chat_id)
            .order_by(func.random())
            .limit(1)
        )
        return await self.session.scalar(stmt)


__all__ = ["ChatParticipantRepository"]
