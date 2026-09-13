import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ChatParticipant
from .base import Base

logger = logging.getLogger(__name__)


class ChatParticipantRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_message(self, chat_id: int, telegram_id: int) -> None:
        """Отмечает "этот юзер написал в этом чате" - вызывается на КАЖДОЕ
        сообщение в группе (см. SyncEntitiesService.sync). Календарные окна
        (сегодня/неделя/месяц) считаются лениво прямо в UPDATE - сравнением
        сохранённого `last_seen_at` с текущим моментом: если граница
        (полночь/понедельник/1-е число) уже пройдена, счётчик обнуляется до
        1 этим же запросом, а не отдельным сбросом по расписанию (тот же
        приём, что уже используется для голода/регена - ленивая
        материализация, не фоновый cron). `date_trunc('week', ...)` в
        Postgres считает неделю с понедельника - ровно то, что нужно.

        Один INSERT ... ON CONFLICT DO UPDATE, без чтения перед записью -
        под конкурентными сообщениями от разных участников гонки нет."""

        same_day = func.date_trunc(
            "day", ChatParticipant.last_seen_at
        ) == func.date_trunc("day", func.now())
        same_week = func.date_trunc(
            "week", ChatParticipant.last_seen_at
        ) == func.date_trunc("week", func.now())
        same_month = func.date_trunc(
            "month", ChatParticipant.last_seen_at
        ) == func.date_trunc("month", func.now())

        stmt = (
            insert(ChatParticipant)
            .values(
                chat_id=chat_id,
                telegram_id=telegram_id,
                messages_total=1,
                messages_today=1,
                messages_week=1,
                messages_month=1,
            )
            .on_conflict_do_update(
                index_elements=["chat_id", "telegram_id"],
                set_={
                    "last_seen_at": func.now(),
                    "messages_total": ChatParticipant.messages_total + 1,
                    "messages_today": case(
                        (same_day, ChatParticipant.messages_today + 1), else_=1
                    ),
                    "messages_week": case(
                        (same_week, ChatParticipant.messages_week + 1), else_=1
                    ),
                    "messages_month": case(
                        (same_month, ChatParticipant.messages_month + 1), else_=1
                    ),
                },
            )
        )
        await self.session.execute(stmt)

    async def record_join(
        self,
        chat_id: int,
        telegram_id: int,
        joined_at: datetime,
        join_method: str,
    ) -> None:
        """Пишется ОДИН раз на само событие входа (`ChatMemberUpdated`,
        JOIN_TRANSITION) - joined_at/join_method обновляются, даже если
        строка уже существовала (сообщения раньше события входа - редкий,
        но возможный порядок апдейтов), счётчики сообщений при этом не
        трогаются вообще."""

        stmt = (
            insert(ChatParticipant)
            .values(
                chat_id=chat_id,
                telegram_id=telegram_id,
                joined_at=joined_at,
                join_method=join_method,
            )
            .on_conflict_do_update(
                index_elements=["chat_id", "telegram_id"],
                set_={"joined_at": joined_at, "join_method": join_method},
            )
        )
        await self.session.execute(stmt)

    async def remove(self, chat_id: int, telegram_id: int) -> None:
        """Выход из чата - строка удаляется целиком ("регистрация И
        удаление", не мягкий флаг) - повторный вход начинает с чистого
        листа (новый joined_at, счётчики с нуля)."""

        await self.session.execute(
            delete(ChatParticipant).where(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.telegram_id == telegram_id,
            )
        )

    async def get_random_participant(self, chat_id: int) -> Optional[int]:
        """Возвращает telegram_id случайного участника этого чата, или
        None, если для чата ещё никого не записано."""

        stmt = (
            select(ChatParticipant.telegram_id)
            .where(ChatParticipant.chat_id == chat_id)
            .order_by(func.random())
            .limit(1)
        )
        return await self.session.scalar(stmt)


__all__ = ["ChatParticipantRepository"]
