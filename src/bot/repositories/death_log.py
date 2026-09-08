import logging
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import DeathLog
from .base import Base

logger = logging.getLogger(__name__)


class DeathLogRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        telegram_id: int,
        cause: str,
        level: int,
        lifetime_rc_earned: int,
        killer_telegram_id: Optional[int] = None,
    ) -> DeathLog:
        stmt = (
            insert(DeathLog)
            .values(
                telegram_id=telegram_id,
                cause=cause,
                level=level,
                lifetime_rc_earned=lifetime_rc_earned,
                killer_telegram_id=killer_telegram_id,
            )
            .returning(DeathLog)
        )

        death_log = await self.session.scalar(stmt)

        if not death_log:
            raise ValueError("Не удалось создать запись лога смерти")

        return death_log

    async def get_latest(self, telegram_id: int) -> Optional[DeathLog]:
        """Последняя смерть этого telegram_id - читается для некролога
        (снапшот на момент смерти, а не живая строка Ghoul, которая к
        моменту отправки уведомления могла уже быть сброшена возрождением)."""

        stmt = (
            select(DeathLog)
            .where(DeathLog.telegram_id == telegram_id)
            .order_by(desc(DeathLog.created_at))
            .limit(1)
        )
        return await self.session.scalar(stmt)
