import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Transfer
from ..utils import utcnow_naive
from .base import Base

logger = logging.getLogger(__name__)


class TransferRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(self, sender_id: int, receiver_id: int, amount: int) -> Transfer:
        stmt = (
            insert(Transfer)
            .values(sender_id=sender_id, receiver_id=receiver_id, amount=amount)
            .returning(Transfer)
        )

        transfer = await self.session.scalar(stmt)

        if not transfer:
            raise ValueError("Не удалось создать запись о переводе")

        return transfer

    async def count_received_since(self, receiver_id: int, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(Transfer)
            .where(
                Transfer.receiver_id == receiver_id,
                Transfer.created_at >= since,
            )
        )

        count = await self.session.scalar(stmt)
        return count or 0

    async def count_received_last_24h(self, receiver_id: int) -> int:
        since = utcnow_naive() - timedelta(hours=24)
        return await self.count_received_since(receiver_id, since)
