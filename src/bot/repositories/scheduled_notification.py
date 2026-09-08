import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ScheduledNotification

from .base import Base

logger = logging.getLogger(__name__)


class ScheduledNotificationRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def schedule(
        self,
        telegram_id: int,
        notification_type: str,
        fire_at: datetime,
        threshold: Optional[int] = None,
    ) -> None:
        """Ставит (или переставляет, если уже есть) один активный пуш для
        пары (telegram_id, notification_type). Не история - строка одна на
        пару, целиком перезаписывается при каждом пересчёте расписания."""

        await self.session.execute(
            insert(ScheduledNotification)
            .values(
                telegram_id=telegram_id,
                notification_type=notification_type,
                threshold=threshold,
                fire_at=fire_at,
            )
            .on_conflict_do_update(
                index_elements=["telegram_id", "notification_type"],
                set_={"threshold": threshold, "fire_at": fire_at},
            )
        )

    async def delete(self, telegram_id: int, notification_type: str) -> None:
        await self.session.execute(
            delete(ScheduledNotification).where(
                ScheduledNotification.telegram_id == telegram_id,
                ScheduledNotification.notification_type == notification_type,
            )
        )

    async def get_due(self, now: datetime) -> list[ScheduledNotification]:
        result = await self.session.execute(
            select(ScheduledNotification).where(ScheduledNotification.fire_at <= now)
        )
        return list(result.scalars().all())


__all__ = ["ScheduledNotificationRepository"]
