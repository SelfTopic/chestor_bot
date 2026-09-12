import logging
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ActiveBattle

from .base import Base

logger = logging.getLogger(__name__)


class ActiveBattleRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def try_claim(self, rows: List[dict]) -> bool:
        """Пытается ОДНОЙ INSERT-командой занять ВСЕХ участников разом
        (одна строка на telegram_id в `rows`) - см. BattleRecordService для
        готовых сценариев (моб/дуэль). Либо все успешно заняты (PK-
        конфликтов не было ни у одного), либо НИ ОДИН - если хоть один
        telegram_id уже занят другим боем, откатывает то, что успело
        вставиться для остальных (частичный захват хуже полного отказа -
        иначе ровно тот эксплойт с "одновременно двумя боями", ради
        которого эта таблица и придумана, но только для другой стороны)."""

        if not rows:
            return True

        stmt = (
            insert(ActiveBattle)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["telegram_id"])
            .returning(ActiveBattle.telegram_id)
        )
        claimed = (await self.session.scalars(stmt)).all()

        if len(claimed) != len(rows):
            if claimed:
                await self.session.execute(
                    delete(ActiveBattle).where(ActiveBattle.telegram_id.in_(claimed))
                )
            logger.debug(f"Partial/failed battle claim ({len(claimed)}/{len(rows)}) - rolled back")
            return False

        return True

    async def release(self, telegram_ids: List[int]) -> None:
        if not telegram_ids:
            return
        await self.session.execute(
            delete(ActiveBattle).where(ActiveBattle.telegram_id.in_(telegram_ids))
        )

    async def get(self, telegram_id: int) -> Optional[ActiveBattle]:
        return await self.session.scalar(
            select(ActiveBattle).where(ActiveBattle.telegram_id == telegram_id)
        )


__all__ = ["ActiveBattleRepository"]
