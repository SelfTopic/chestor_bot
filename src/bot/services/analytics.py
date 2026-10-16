import logging
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories import ActivityKey, AnalyticsRepository, EventRecord

logger = logging.getLogger(__name__)

# «Сегодня» для игроков — московское: по нему и считаются дни активности.
MOSCOW = ZoneInfo("Europe/Moscow")
FLUSH_INTERVAL = 10.0
# Пока база недоступна, записи ждут в памяти, но не бесконечно.
MAX_PENDING_EVENTS = 50_000


class AnalyticsRecorder:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._session_factory = session_factory
        self._now = now
        self._events: list[EventRecord] = []
        self._activity: Counter[ActivityKey] = Counter()

    def command(
        self,
        *,
        handler: str,
        update_kind: str,
        user_id: int | None,
        chat_id: int | None,
        chat_type: str | None,
        seconds: float,
    ) -> None:
        if len(self._events) >= MAX_PENDING_EVENTS:
            return
        self._events.append(
            EventRecord(
                at=self._now().replace(tzinfo=None),
                handler=handler,
                update_kind=update_kind,
                user_id=user_id,
                chat_id=chat_id,
                chat_type=chat_type,
                duration_ms=round(seconds * 1000),
            )
        )

    def message(self, *, chat_id: int, user_id: int, chat_type: str) -> None:
        day = self._now().astimezone(MOSCOW).date()
        self._activity[ActivityKey(day, chat_id, user_id, chat_type)] += 1

    async def flush(self) -> None:
        events, self._events = self._events, []
        activity, self._activity = self._activity, Counter()
        if not events and not activity:
            return
        try:
            async with self._session_factory() as session:
                repository = AnalyticsRepository(session)
                await repository.add_events(events)
                await repository.add_activity(dict(activity))
                await session.commit()
        except Exception:
            logger.warning("Статистика не записалась, повторю позже", exc_info=True)
            self._events = (events + self._events)[:MAX_PENDING_EVENTS]
            self._activity.update(activity)


__all__ = ["AnalyticsRecorder", "FLUSH_INTERVAL"]
