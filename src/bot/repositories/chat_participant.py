from datetime import datetime
from typing import Optional

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ChatParticipant, User


class ChatParticipantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_message(self, chat_id: int, telegram_id: int) -> None:
        # Календарные окна сбрасываются лениво в том же UPDATE: если граница
        # (полночь, понедельник, 1-е число) после last_seen_at пройдена, счётчик снова 1.
        def same(period: str):
            return func.date_trunc(period, ChatParticipant.last_seen_at) == func.date_trunc(
                period, func.now()
            )

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
                        (same("day"), ChatParticipant.messages_today + 1), else_=1
                    ),
                    "messages_week": case(
                        (same("week"), ChatParticipant.messages_week + 1), else_=1
                    ),
                    "messages_month": case(
                        (same("month"), ChatParticipant.messages_month + 1), else_=1
                    ),
                },
            )
        )
        await self.session.execute(stmt)

    async def record_join(
        self, chat_id: int, telegram_id: int, joined_at: datetime, join_method: str
    ) -> None:
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
        await self.session.execute(
            delete(ChatParticipant).where(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.telegram_id == telegram_id,
            )
        )

    async def random_participant(self, chat_id: int) -> Optional[User]:
        stmt = (
            select(User)
            .join(ChatParticipant, ChatParticipant.telegram_id == User.telegram_id)
            .where(ChatParticipant.chat_id == chat_id)
            .order_by(func.random())
            .limit(1)
        )
        return await self.session.scalar(stmt)
