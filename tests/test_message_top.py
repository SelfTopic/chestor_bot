"""«топ» / «стата»: самые активные участники чата по сообщениям — за всё время или за
скользящие 24 часа, 7 и 30 дней (почасовые счётчики chat_message_hours)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import insert, select

from src.bot.dialogs import Dialogs
from src.bot.services.analytics import AnalyticsRecorder
from src.bot.tasks import MessageHoursCleanup
from src.database.models import ChatMessageHour

from .conftest import (
    chat_member_update,
    matches_phrase,
    message_update,
    only_text,
    owner_dict,
    phrase_texts,
)

GROUP = -100500


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def top_reply(title, *rows: tuple[str, int]) -> str:
    lines = "\n".join(
        only_text(Dialogs.tops.messages.row(place=place, name=name, messages=messages))
        for place, (name, messages) in enumerate(rows, start=1)
    )
    return only_text(Dialogs.tops.messages.message(title=only_text(title), rows=lines))


@pytest.fixture
async def chatters(feed, telegram):
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    for uid, name, count in ((1, "Альфа", 3), (2, "Бета", 1), (3, "Гамма", 2)):
        for _ in range(count):
            await feed(message_update("привет", uid=uid, first_name=name, chat=GROUP))


async def add_hours(session_factory, *rows: tuple[int, timedelta, int]) -> None:
    async with session_factory() as session:
        await session.execute(
            insert(ChatMessageHour),
            [
                dict(hour=now() - ago, chat_id=GROUP, user_id=uid, messages=messages)
                for uid, ago, messages in rows
            ],
        )
        await session.commit()


async def test_all_time_top_counts_every_message_of_current_members(send, chatters):
    (reply,) = await send("стата", uid=2, first_name="Бета", chat=GROUP)

    assert reply == top_reply(
        Dialogs.tops.messages.title_all(), ("Альфа", 3), ("Бета", 2), ("Гамма", 2)
    )


async def test_member_who_left_drops_out_of_the_top(send, feed, chatters):
    await feed(chat_member_update(1, GROUP, "member", "left"))

    (reply,) = await send("топ", uid=3, first_name="Гамма", chat=GROUP)

    assert reply == top_reply(Dialogs.tops.messages.title_all(), ("Гамма", 3), ("Бета", 1))


@pytest.mark.parametrize(
    ("text", "title", "expected"),
    [
        ("топ день", Dialogs.tops.messages.title_day(), [("Бета", 5)]),
        ("Топ Неделя", Dialogs.tops.messages.title_week(), [("Гамма", 7), ("Бета", 5)]),
        ("top month", Dialogs.tops.messages.title_month(), [("Альфа", 20), ("Гамма", 7), ("Бета", 5)]),
    ],
)
async def test_periods_are_rolling_windows(
    send, chatters, session_factory, text, title, expected
):
    await add_hours(
        session_factory,
        (2, timedelta(hours=2), 5),
        (3, timedelta(days=3), 7),
        (1, timedelta(days=20), 20),
        (1, timedelta(days=40), 100),
    )

    (reply,) = await send(text, uid=99, chat=GROUP)

    assert reply == top_reply(title, *expected)


async def test_empty_period(send, chatters):
    (reply,) = await send("топ день", uid=1, first_name="Альфа", chat=GROUP)

    assert reply in phrase_texts(Dialogs.tops.messages.empty())


async def test_private_chat_has_no_message_top(send):
    (reply,) = await send("топ")

    assert reply == only_text(Dialogs.tops.messages.only_group())


async def test_other_words_after_top_are_not_a_period(send, chatters):
    assert await send("топ год", uid=1, chat=GROUP) == []
    (reply,) = await send("топ бал", uid=1, chat=GROUP)
    assert matches_phrase(reply, "tops.balance.message")


async def test_group_messages_are_counted_per_hour(session_factory):
    moment = datetime(2026, 10, 14, 22, 30, tzinfo=timezone.utc)
    recorder = AnalyticsRecorder(session_factory, now=lambda: moment)

    recorder.message(chat_id=GROUP, user_id=7, chat_type="supergroup")
    recorder.message(chat_id=GROUP, user_id=7, chat_type="supergroup")
    recorder.message(chat_id=7, user_id=7, chat_type="private")
    await recorder.flush()

    async with session_factory() as session:
        (row,) = await session.scalars(select(ChatMessageHour))
    assert (row.hour, row.chat_id, row.user_id, row.messages) == (
        datetime(2026, 10, 14, 22),
        GROUP,
        7,
        2,
    )


async def test_cleanup_forgets_hours_older_than_a_month(dispatcher, chatters, session_factory):
    await add_hours(session_factory, (1, timedelta(days=29), 1), (1, timedelta(days=32), 1))

    await dispatcher.run_task(MessageHoursCleanup)

    async with session_factory() as session:
        hours = list(await session.scalars(select(ChatMessageHour.hour)))
    assert len(hours) == 1 and hours[0] > now() - timedelta(days=30)
