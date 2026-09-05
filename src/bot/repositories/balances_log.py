import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import BalancesLog
from .base import Base

logger = logging.getLogger(__name__)


class BalancesLogRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        telegram_id: int,
        change_balance: int,
        before_balance: int,
        after_balance: int,
        log: str,
    ) -> BalancesLog:
        stmt = (
            insert(BalancesLog)
            .values(
                telegram_id=telegram_id,
                change_balance=change_balance,
                before_balance=before_balance,
                after_balance=after_balance,
                log=log,
            )
            .returning(BalancesLog)
        )

        balances_log = await self.session.scalar(stmt)

        if not balances_log:
            raise ValueError("Не удалось создать запись лога баланса")

        return balances_log
