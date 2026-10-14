from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import insert as sa_insert
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import BotEvent, ChatActivity
from .base import Base


@dataclass(frozen=True)
class EventRecord:
    at: datetime
    handler: str
    update_kind: str
    user_id: int | None
    chat_id: int | None
    chat_type: str | None
    duration_ms: int


@dataclass(frozen=True)
class ActivityKey:
    day: date
    chat_id: int
    user_id: int
    chat_type: str


class AnalyticsRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_events(self, events: Sequence[EventRecord]) -> None:
        if not events:
            return
        await self.session.execute(
            sa_insert(BotEvent),
            [
                dict(
                    at=event.at,
                    handler=event.handler,
                    update_kind=event.update_kind,
                    user_id=event.user_id,
                    chat_id=event.chat_id,
                    chat_type=event.chat_type,
                    duration_ms=event.duration_ms,
                )
                for event in events
            ],
        )

    async def add_activity(self, counts: dict[ActivityKey, int]) -> None:
        if not counts:
            return
        stmt = insert(ChatActivity).values(
            [
                dict(
                    day=key.day,
                    chat_id=key.chat_id,
                    user_id=key.user_id,
                    chat_type=key.chat_type,
                    messages=messages,
                )
                for key, messages in counts.items()
            ]
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[ChatActivity.day, ChatActivity.chat_id, ChatActivity.user_id],
                set_={"messages": ChatActivity.messages + stmt.excluded.messages},
            )
        )
