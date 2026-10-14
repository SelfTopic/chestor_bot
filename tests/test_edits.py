"""Эдиты по «Токийскому гулю»: юзербот пересылает боту посты каналов с видео, бот хранит
file_id, а на «1000-7» отвечает случайным эдитом."""

from typing import Any

import pytest
from sqlalchemy import select

from src.bot.dialogs import Dialogs
from src.config import settings
from src.database.models import GhoulEdit

from .conftest import message_update, phrase_texts

USERBOT = 555
CHANNEL = -1001234


@pytest.fixture(autouse=True)
def userbot(monkeypatch) -> None:
    monkeypatch.setattr(settings, "EDITS_USERBOT_ID", USERBOT)


def forwarded(file_id: str, post: int, uid: int = USERBOT) -> dict[str, Any]:
    return message_update(
        None,
        uid=uid,
        video={
            "file_id": file_id,
            "file_unique_id": f"u{file_id}",
            "width": 720,
            "height": 1280,
            "duration": 30,
        },
        forward_origin={
            "type": "channel",
            "chat": {"id": CHANNEL, "type": "channel", "title": "edits"},
            "message_id": post,
            "date": 4,
        },
    )


async def edits(session_factory) -> list[tuple[str, int, int]]:
    async with session_factory() as session:
        rows = await session.scalars(select(GhoulEdit).order_by(GhoulEdit.id))
        return [(row.file_id, row.channel_id, row.channel_message_id) for row in rows]


async def test_userbot_forwards_are_stored_once_and_silently(feed, telegram, session_factory):
    for update in (forwarded("EDIT1", 10), forwarded("EDIT1", 10), forwarded("EDIT2", 11)):
        await feed(update)
        assert telegram.calls == []

    assert await edits(session_factory) == [("EDIT1", CHANNEL, 10), ("EDIT2", CHANNEL, 11)]


async def test_forwards_from_anyone_else_are_ignored(feed, session_factory):
    await feed(forwarded("EDIT1", 10, uid=777))

    assert await edits(session_factory) == []


async def test_1000_minus_7_sends_a_stored_edit(feed, send, telegram):
    (empty,) = await send("1000-7")
    assert empty in phrase_texts(Dialogs.fun.edits.empty())

    await feed(forwarded("EDIT1", 10))
    await feed(message_update("1000-7"))

    (video,) = telegram.bodies("sendVideo")
    assert video["video"] == "EDIT1"
    assert "caption" not in video
