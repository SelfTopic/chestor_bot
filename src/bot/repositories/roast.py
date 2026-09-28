from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Battle, Ghoul, RoastLog, User
from .base import Base


@dataclass(frozen=True)
class PlayerFacts:
    balance: int
    level: Optional[int]
    snap_count: int
    coffee_count: int
    deaths: int
    wins: int
    losses: int


class RoastRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def player_facts(self, telegram_id: int) -> Optional[PlayerFacts]:
        won = or_(
            (Battle.participant_a_telegram_id == telegram_id) & (Battle.winner == "a"),
            (Battle.participant_b_telegram_id == telegram_id) & (Battle.winner == "b"),
        )
        lost = or_(
            (Battle.participant_a_telegram_id == telegram_id) & (Battle.winner == "b"),
            (Battle.participant_b_telegram_id == telegram_id) & (Battle.winner == "a"),
        )
        wins = select(func.count()).select_from(Battle).where(won).scalar_subquery()
        losses = select(func.count()).select_from(Battle).where(lost).scalar_subquery()
        stmt = (
            select(
                User.balance,
                Ghoul.level,
                Ghoul.snap_count,
                Ghoul.coffee_count,
                Ghoul.deaths,
                wins,
                losses,
            )
            .outerjoin(Ghoul, Ghoul.telegram_id == User.telegram_id)
            .where(User.telegram_id == telegram_id)
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        balance, level, snaps, coffee, deaths, won_count, lost_count = row
        return PlayerFacts(
            balance=balance,
            level=level,
            snap_count=snaps or 0,
            coffee_count=coffee or 0,
            deaths=deaths or 0,
            wins=won_count,
            losses=lost_count,
        )

    async def argument_history(
        self, chat_id: int, telegram_id: int, window: timedelta, limit: int
    ) -> list[RoastLog]:
        # Время сравнивается с часами БД: created_at ставит сервер Postgres.
        stmt = (
            select(RoastLog)
            .where(
                RoastLog.chat_id == chat_id,
                RoastLog.telegram_id == telegram_id,
                RoastLog.created_at >= func.now() - window,
                RoastLog.reply.is_not(None),
                RoastLog.filtered.is_(False),
            )
            .order_by(RoastLog.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(await self.session.scalars(stmt))))

    async def good_examples(self, limit: int) -> list[RoastLog]:
        stmt = (
            select(RoastLog)
            .where(RoastLog.rating > 0, RoastLog.reply.is_not(None))
            .order_by(func.random())
            .limit(limit)
        )
        return list(await self.session.scalars(stmt))

    async def add(self, entry: RoastLog) -> RoastLog:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def set_bot_message(self, log_id: int, bot_message_id: int) -> None:
        await self.session.execute(
            update(RoastLog).where(RoastLog.id == log_id).values(bot_message_id=bot_message_id)
        )

    async def add_followup(self, log_id: int) -> None:
        await self.session.execute(
            update(RoastLog)
            .where(RoastLog.id == log_id)
            .values(followups=RoastLog.followups + 1)
        )

    async def rate(self, chat_id: int, bot_message_id: int, rating: int) -> bool:
        result = await self.session.execute(
            update(RoastLog)
            .where(RoastLog.chat_id == chat_id, RoastLog.bot_message_id == bot_message_id)
            .values(rating=rating)
            .returning(RoastLog.id)
        )
        return result.first() is not None

    async def delete_older_than(self, age: timedelta) -> None:
        await self.session.execute(
            delete(RoastLog).where(RoastLog.created_at < func.now() - age)
        )
