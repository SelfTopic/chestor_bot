import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Battle

from .base import Base

logger = logging.getLogger(__name__)


class BattleRepository(Base):
    """Постоянная история (BATTLE_ENGINE.md 5.1) - append-only, строки
    никогда не обновляются/не удаляются (та же дисциплина, что у
    DeathLogRepository)."""

    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        battle_type: str,
        participant_a_telegram_id: int,
        participant_b_telegram_id: Optional[int],
        mob_name: Optional[str],
        winner: Optional[str],
        ended_naturally: bool,
        is_forced: bool = False,
        winner_choice: Optional[str] = None,
        reward_level_progress: Optional[float] = None,
        reward_rc: Optional[int] = None,
        reward_balance: Optional[int] = None,
    ) -> Battle:
        stmt = (
            insert(Battle)
            .values(
                battle_type=battle_type,
                participant_a_telegram_id=participant_a_telegram_id,
                participant_b_telegram_id=participant_b_telegram_id,
                mob_name=mob_name,
                winner=winner,
                ended_naturally=ended_naturally,
                is_forced=is_forced,
                winner_choice=winner_choice,
                reward_level_progress=reward_level_progress,
                reward_rc=reward_rc,
                reward_balance=reward_balance,
            )
            .returning(Battle)
        )
        battle = await self.session.scalar(stmt)

        if not battle:
            raise ValueError("Не удалось записать историю боя")

        return battle

    async def count_total_since(self, telegram_id: int, since: datetime) -> int:
        """Для дневного лимита "20 боёв/сутки всего" (4.4) - гуль мог быть
        любой из двух сторон дуэли, отсюда `or_`."""

        stmt = (
            select(func.count())
            .select_from(Battle)
            .where(
                Battle.created_at >= since,
                or_(
                    Battle.participant_a_telegram_id == telegram_id,
                    Battle.participant_b_telegram_id == telegram_id,
                ),
            )
        )
        return (await self.session.scalar(stmt)) or 0

    async def count_pair_since(
        self, telegram_id_a: int, telegram_id_b: int, since: datetime
    ) -> int:
        """Для дневного лимита "5 боёв/сутки на пару" (4.4) - порядок a/b
        в конкретной записи не гарантирован (кто на чьей стороне был при
        записи - деталь одного конкретного боя), поэтому проверяем оба
        варианта пары."""

        stmt = (
            select(func.count())
            .select_from(Battle)
            .where(
                Battle.created_at >= since,
                or_(
                    (Battle.participant_a_telegram_id == telegram_id_a)
                    & (Battle.participant_b_telegram_id == telegram_id_b),
                    (Battle.participant_a_telegram_id == telegram_id_b)
                    & (Battle.participant_b_telegram_id == telegram_id_a),
                ),
            )
        )
        return (await self.session.scalar(stmt)) or 0


__all__ = ["BattleRepository"]
