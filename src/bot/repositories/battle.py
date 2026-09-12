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

    async def count_wins(self, telegram_id: int, battle_type: Optional[str] = None) -> int:
        """Побед за всё время (BATTLE_ENGINE.md 5.2) - НЕ по 24ч окну, в
        отличие от count_total_since/count_pair_since (те - под дневные
        лимиты). Работает и для боёв с мобами (participant_b - NULL,
        winner="a"/"b" относительно самого игрока, см. BattleRecordService.
        record_mob_fight).

        `battle_type=None` - ЛЮБОЙ тип боя разом (дуэли и мобы вперемешку -
        ВАЖНО: не использовать это значение там, где счёт должен быть
        честным по одному виду соперника, см. чат про "смешанные значения
        счётчиков"). "duel"/"mob" - строго один тип."""

        conditions = [
            or_(
                (Battle.participant_a_telegram_id == telegram_id) & (Battle.winner == "a"),
                (Battle.participant_b_telegram_id == telegram_id) & (Battle.winner == "b"),
            )
        ]
        if battle_type is not None:
            conditions.append(Battle.battle_type == battle_type)

        stmt = select(func.count()).select_from(Battle).where(*conditions)
        return (await self.session.scalar(stmt)) or 0

    async def count_losses(self, telegram_id: int, battle_type: Optional[str] = None) -> int:
        conditions = [
            or_(
                (Battle.participant_a_telegram_id == telegram_id) & (Battle.winner == "b"),
                (Battle.participant_b_telegram_id == telegram_id) & (Battle.winner == "a"),
            )
        ]
        if battle_type is not None:
            conditions.append(Battle.battle_type == battle_type)

        stmt = select(func.count()).select_from(Battle).where(*conditions)
        return (await self.session.scalar(stmt)) or 0

    async def count_total(self, telegram_id: int, battle_type: Optional[str] = None) -> int:
        """Все бои за всё время (включая ничьи) - победы+поражения+ничьи."""

        conditions = [
            or_(
                Battle.participant_a_telegram_id == telegram_id,
                Battle.participant_b_telegram_id == telegram_id,
            )
        ]
        if battle_type is not None:
            conditions.append(Battle.battle_type == battle_type)

        stmt = select(func.count()).select_from(Battle).where(*conditions)
        return (await self.session.scalar(stmt)) or 0


__all__ = ["BattleRepository"]
