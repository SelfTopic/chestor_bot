from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import QuizStreak

from .base import Base


@dataclass(frozen=True)
class HeldStreak:
    streak: int
    alive: bool


@dataclass(frozen=True)
class ExpiredStreak:
    chat_id: int
    message_id: int
    rich: str
    streak: int


class QuizStreakRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def hold(
        self,
        telegram_id: int,
        chat_id: int,
        message_id: int,
        rich: str,
        streak: int,
        lifetime: timedelta,
    ) -> None:
        values = {
            "chat_id": chat_id,
            "message_id": message_id,
            "rich": rich,
            "streak": streak,
            "expires_at": func.now() + lifetime,
        }
        await self.session.execute(
            insert(QuizStreak)
            .values(telegram_id=telegram_id, **values)
            .on_conflict_do_update(index_elements=["telegram_id"], set_=values)
        )

    # None — серию уже забрал тикер или это сообщение не её последнее.
    async def take(self, telegram_id: int, message_id: int) -> HeldStreak | None:
        row = (
            await self.session.execute(
                delete(QuizStreak)
                .where(QuizStreak.telegram_id == telegram_id, QuizStreak.message_id == message_id)
                .returning(QuizStreak.streak, QuizStreak.expires_at > func.now())
            )
        ).one_or_none()
        return HeldStreak(streak=row[0], alive=row[1]) if row else None

    async def take_expired(self) -> list[ExpiredStreak]:
        rows = await self.session.execute(
            delete(QuizStreak)
            .where(QuizStreak.expires_at <= func.now())
            .returning(
                QuizStreak.chat_id,
                QuizStreak.message_id,
                QuizStreak.rich,
                QuizStreak.streak,
            )
        )
        return [ExpiredStreak(*row) for row in rows.tuples()]


__all__ = ["ExpiredStreak", "HeldStreak", "QuizStreakRepository"]
