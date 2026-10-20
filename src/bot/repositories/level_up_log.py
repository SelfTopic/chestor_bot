import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import LevelUpLog
from .base import Base

logger = logging.getLogger(__name__)


class LevelUpLogRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        telegram_id: int,
        source: str,
        level: int,
        cheston_reward: int,
        rc_reward: int,
    ) -> LevelUpLog:
        stmt = (
            insert(LevelUpLog)
            .values(
                telegram_id=telegram_id,
                source=source,
                level=level,
                cheston_reward=cheston_reward,
                rc_reward=rc_reward,
            )
            .returning(LevelUpLog)
        )

        level_up_log = await self.session.scalar(stmt)

        if not level_up_log:
            raise ValueError("Не удалось создать запись лога level-up")

        return level_up_log
