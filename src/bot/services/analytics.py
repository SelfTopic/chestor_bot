import logging
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories import (
    ActivityKey,
    AnalyticsRepository,
    EventRecord,
    MessageHourKey,
    UserRepository,
)

logger = logging.getLogger(__name__)

# «Сегодня» для игроков — московское: по нему и считаются дни активности.
MOSCOW = ZoneInfo("Europe/Moscow")
FLUSH_INTERVAL = 10.0
# Пока база недоступна, записи ждут в памяти, но не бесконечно.
MAX_PENDING_EVENTS = 50_000
GROUP_TYPES = ("group", "supergroup")
# Самое длинное окно топа сообщений — 30 дней; час запаса на неполный первый час.
MESSAGE_HOURS_KEPT = timedelta(days=30, hours=1)


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
        self._message_hours: Counter[MessageHourKey] = Counter()
        self._last_seen: dict[int, datetime] = {}

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
        now = self._now()
        self._activity[ActivityKey(now.astimezone(MOSCOW).date(), chat_id, user_id, chat_type)] += 1
        if chat_type in GROUP_TYPES:
            hour = now.replace(minute=0, second=0, microsecond=0, tzinfo=None)
            self._message_hours[MessageHourKey(hour, chat_id, user_id)] += 1

    # Любое действие игрока, а не только сообщения в чатах: личка и кнопки тоже активность.
    def touch(self, user_id: int) -> None:
        self._merge_last_seen({user_id: self._now().replace(tzinfo=None)})

    async def flush(self) -> None:
        events, self._events = self._events, []
        activity, self._activity = self._activity, Counter()
        message_hours, self._message_hours = self._message_hours, Counter()
        last_seen, self._last_seen = self._last_seen, {}
        if not events and not activity and not message_hours and not last_seen:
            return
        try:
            async with self._session_factory() as session:
                repository = AnalyticsRepository(session)
                await repository.add_events(events)
                await repository.add_activity(dict(activity))
                await repository.add_message_hours(dict(message_hours))
                await UserRepository(session).bump_last_active(last_seen)
                await session.commit()
        except Exception:
            logger.warning("Статистика не записалась, повторю позже", exc_info=True)
            self._events = (events + self._events)[:MAX_PENDING_EVENTS]
            self._activity.update(activity)
            self._message_hours.update(message_hours)
            self._merge_last_seen(last_seen)

    async def forget_old_message_hours(self) -> None:
        moment = (self._now() - MESSAGE_HOURS_KEPT).replace(tzinfo=None)
        async with self._session_factory() as session:
            await AnalyticsRepository(session).delete_message_hours_before(moment)
            await session.commit()

    def _merge_last_seen(self, seen: dict[int, datetime]) -> None:
        for user_id, at in seen.items():
            current = self._last_seen.get(user_id)
            if current is None or at > current:
                self._last_seen[user_id] = at


__all__ = ["AnalyticsRecorder", "FLUSH_INTERVAL"]
