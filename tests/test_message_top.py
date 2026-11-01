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


def top_reply(title, rows: list[tuple[str, int]], total, you: tuple[int, int] | None) -> str:
    lines = "\n".join(
        only_text(Dialogs.tops.messages.row(place=place, name=name, messages=messages))
        for place, (name, messages) in enumerate(rows, start=1)
    )
    you_line = (
        Dialogs.tops.you_absent()
        if you is None
        else Dialogs.tops.you(place=you[0], value=you[1])
    )
    return only_text(
        Dialogs.tops.messages.message(
            title=only_text(title), rows=lines, total=only_text(total), you=only_text(you_line)
        )
    )


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
        Dialogs.tops.messages.title_all(),
        [("Альфа", 3), ("Бета", 2), ("Гамма", 2)],
        Dialogs.tops.messages.total_all(count=7),
        you=(2, 2),
    )


async def test_member_who_left_drops_out_of_the_top(send, feed, chatters):
    await feed(chat_member_update(1, GROUP, "member", "left"))

    (reply,) = await send("топ", uid=3, first_name="Гамма", chat=GROUP)

    assert reply == top_reply(
        Dialogs.tops.messages.title_all(),
        [("Гамма", 3), ("Бета", 1)],
        Dialogs.tops.messages.total_all(count=4),
        you=(1, 3),
    )


messages = Dialogs.tops.messages


@pytest.mark.parametrize(
    ("text", "uid", "title", "expected", "total", "you"),
    [
        ("топ день", 99, messages.title_day(), [("Бета", 5)], messages.total_day(count=5), None),
        (
            "Топ Неделя",
            3,
            messages.title_week(),
            [("Гамма", 7), ("Бета", 5)],
            messages.total_week(count=12),
            (1, 7),
        ),
        (
            "top month",
            2,
            messages.title_month(),
            [("Альфа", 20), ("Гамма", 7), ("Бета", 5)],
            messages.total_month(count=32),
            (3, 5),
        ),
    ],
)
async def test_periods_are_rolling_windows(
    send, chatters, session_factory, text, uid, title, expected, total, you
):
    await add_hours(
        session_factory,
        (2, timedelta(hours=2), 5),
        (3, timedelta(days=3), 7),
        (1, timedelta(days=20), 20),
        (1, timedelta(days=40), 100),
    )

    names = {2: "Бета", 3: "Гамма", 99: "Владелец"}
    (reply,) = await send(text, uid=uid, first_name=names[uid], chat=GROUP)

    assert reply == top_reply(title, expected, total, you)


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
