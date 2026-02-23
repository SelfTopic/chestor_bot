import logging
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Lottery
from .base import Base

logger = logging.getLogger(__name__)


class LotteryRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        telegram_id: int,
        bet_amount: int,
        chosen_color: str,
        winning_color: str,
        is_won: bool,
        earned: int,
        video_file_id: Optional[str] = None,
    ) -> Lottery:
        stmt = (
            insert(Lottery)
            .values(
                telegram_id=telegram_id,
                bet_amount=bet_amount,
                chosen_color=chosen_color,
                winning_color=winning_color,
                is_won=is_won,
                earned=earned,
                video_file_id=video_file_id,
            )
            .returning(Lottery)
        )

        lottery = await self.session.scalar(stmt)

        if not lottery:
            raise ValueError("Не удалось создать запись в истории ставок")

        return lottery

    async def get_by_id(self, lottery_id: int) -> Optional[Lottery]:
        stmt = select(Lottery).filter(Lottery.id == lottery_id)
        lottery = await self.session.scalar(stmt)

        return lottery

    async def get_by_user_id(self, telegram_id: int) -> list[Lottery]:
        stmt = select(Lottery).filter(Lottery.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        lotteries = result.scalars().all()

        return list(lotteries)

    async def get_recent_by_user_id(
        self, telegram_id: int, limit: int = 10
    ) -> list[Lottery]:
        stmt = (
            select(Lottery)
            .filter(Lottery.telegram_id == telegram_id)
            .order_by(Lottery.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        lotteries = result.scalars().all()

        return list(lotteries)

    async def get_user_stats(self, telegram_id: int) -> dict[str, int]:
        stmt = select(Lottery).filter(Lottery.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        lotteries = result.scalars().all()

        total_bet = sum(l.bet_amount for l in lotteries)
        total_earned = sum(l.earned for l in lotteries)
        wins = sum(1 for l in lotteries if l.is_won)
        loses = sum(1 for l in lotteries if not l.is_won)

        return {
            "total_bet": total_bet,
            "total_earned": total_earned,
            "wins": wins,
            "loses": loses,
            "net_profit": total_earned - total_bet,
        }

    async def update_video_file_id(
        self, lottery_id: int, video_file_id: str
    ) -> Lottery:
        stmt = (
            update(Lottery)
            .filter(Lottery.id == lottery_id)
            .values({Lottery.video_file_id: video_file_id})
            .returning(Lottery)
        )
        lottery = await self.session.scalar(stmt)

        if not lottery:
            raise ValueError("Запись в истории ставок не найдена")

        return lottery

    async def delete_by_id(self, lottery_id: int) -> None:
        stmt = delete(Lottery).filter(Lottery.id == lottery_id)
        await self.session.execute(stmt)
