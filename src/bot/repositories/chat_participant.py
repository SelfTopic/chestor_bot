from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from typing import Any

from sqlalchemy import ColumnElement, case, delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ChatMessageHour, ChatParticipant, User


def in_chat(chat_id: int, telegram_id: Any) -> ColumnElement[bool]:
    return exists().where(
        ChatParticipant.chat_id == chat_id, ChatParticipant.telegram_id == telegram_id
    )


@dataclass(frozen=True)
class MessageTopRow:
    telegram_id: int
    first_name: str
    messages: int


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

    # В топ попадают только те, кто сейчас в чате: строку вышедшего участника удаляет remove().
    async def top_messages(
        self, chat_id: int, since: Optional[datetime], limit: int
    ) -> list[MessageTopRow]:
        if since is None:
            messages = ChatParticipant.messages_total
            stmt = select(ChatParticipant.telegram_id, User.first_name, messages).where(
                messages > 0
            )
        else:
            messages = func.sum(ChatMessageHour.messages)
            stmt = (
                select(ChatParticipant.telegram_id, User.first_name, messages)
                .join(
                    ChatMessageHour,
                    (ChatMessageHour.chat_id == ChatParticipant.chat_id)
                    & (ChatMessageHour.user_id == ChatParticipant.telegram_id),
                )
                .where(ChatMessageHour.hour >= since)
                .group_by(ChatParticipant.telegram_id, User.first_name)
            )
        stmt = (
            stmt.join(User, User.telegram_id == ChatParticipant.telegram_id)
            .where(ChatParticipant.chat_id == chat_id)
            .order_by(messages.desc(), ChatParticipant.telegram_id)
            .limit(limit)
        )
        return [MessageTopRow(*row) for row in await self.session.execute(stmt)]
