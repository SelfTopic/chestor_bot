"""Статистика: каждая команда бота — запись в bot_events, каждое сообщение — счётчик в
chat_activity за московский день. Пишется буфером: тест сбрасывает его сам (flush)."""

from datetime import date, datetime, timezone

from sqlalchemy import select

from src.bot.repositories import UserRepository
from src.bot.services.analytics import AnalyticsRecorder
from src.database.models import BotEvent, ChatActivity

from .conftest import message_update, owner_dict
from .test_common_routers import seed
from .test_update_middlewares import get_user

GROUP = -100500


async def events(session_factory) -> list[BotEvent]:
    async with session_factory() as session:
        return list(await session.scalars(select(BotEvent).order_by(BotEvent.id)))


async def activity(session_factory) -> dict[tuple[int, int], int]:
    async with session_factory() as session:
        rows = await session.scalars(select(ChatActivity))
        return {(row.chat_id, row.user_id): row.messages for row in rows}


async def test_command_is_recorded_with_who_where_and_which_handler(
    feed, dispatcher, session_factory
):
    await feed(message_update("/start", uid=42))
    await dispatcher.analytics.flush()

    (event,) = await events(session_factory)
    assert (event.handler, event.update_kind) == ("StartHandler", "Message")
    assert (event.user_id, event.chat_id, event.chat_type) == (42, 42, "private")
    assert await activity(session_factory) == {(42, 42): 1}


async def test_plain_group_messages_count_as_activity_not_as_commands(
    feed, dispatcher, telegram, session_factory
):
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    for uid in (7, 7, 8):
        await feed(message_update("го в доту", uid=uid, chat=GROUP))
    await dispatcher.analytics.flush()

    assert await events(session_factory) == []
    assert await activity(session_factory) == {(GROUP, 7): 2, (GROUP, 8): 1}


async def test_day_is_moscow_and_counts_add_up_across_flushes(session_factory):
    late_evening_utc = datetime(2026, 10, 14, 22, 30, tzinfo=timezone.utc)
    recorder = AnalyticsRecorder(session_factory, now=lambda: late_evening_utc)

    recorder.message(chat_id=GROUP, user_id=7, chat_type="supergroup")
    await recorder.flush()
    recorder.message(chat_id=GROUP, user_id=7, chat_type="supergroup")
    await recorder.flush()

    async with session_factory() as session:
        (row,) = await session.scalars(select(ChatActivity))
    assert (row.day, row.messages) == (date(2026, 10, 15), 2)


async def test_any_update_from_user_bumps_last_active_at(feed, dispatcher, session_factory):
    await feed(message_update("/start", uid=42))
    await dispatcher.analytics.flush()

    user = await get_user(session_factory, 42)
    assert user is not None and user.last_active_at is not None


async def test_last_active_at_keeps_the_latest_timestamp_across_flushes(session_factory):
    await seed(session_factory, 7)
    earlier = datetime(2026, 10, 14, 10, 0)
    later = datetime(2026, 10, 14, 12, 0)
    times = iter([earlier, later])
    recorder = AnalyticsRecorder(session_factory, now=lambda: next(times))

    recorder.touch(7)
    await recorder.flush()
    recorder.touch(7)
    await recorder.flush()

    user = await get_user(session_factory, 7)
    assert user is not None and user.last_active_at == later


async def test_failed_flush_keeps_last_active_at_pending(monkeypatch, session_factory):
    moment = datetime(2026, 10, 14, 12, 0)
    recorder = AnalyticsRecorder(session_factory, now=lambda: moment)
    recorder.touch(7)

    async def boom(self, *_args, **_kwargs):
        raise RuntimeError("база недоступна")

    monkeypatch.setattr(UserRepository, "bump_last_active", boom)
    await recorder.flush()

    assert recorder._last_seen == {7: moment}
