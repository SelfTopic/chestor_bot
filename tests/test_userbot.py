"""Юзербот пересылает боту видео-посты каналов: эдиты (бот отвечает случайным на «1000-7»)
и серии аниме (/anime целиком уходит по file_id). Бот принимает только его пересылки и
на /userbot_sync сообщает последний сохранённый пост каждого канала."""

import json
from typing import Any

import pytest
from sqlalchemy import select

from src.bot.dialogs import Dialogs
from src.config import settings
from src.database.models import AnimeEpisode, GhoulEdit

from .conftest import message_update, only_text, phrase_texts

USERBOT = 555
CHANNEL = -1001234
ANIME = -1005678


@pytest.fixture(autouse=True)
def userbot(monkeypatch) -> None:
    monkeypatch.setattr(settings, "USERBOT_ID", USERBOT)


def forwarded(
    file_id: str, post: int, uid: int = USERBOT, channel: int = CHANNEL, caption: str | None = None
) -> dict[str, Any]:
    extra: dict[str, Any] = {"caption": caption} if caption else {}
    return message_update(
        None,
        uid=uid,
        **extra,
        video={
            "file_id": file_id,
            "file_unique_id": f"u{file_id}",
            "width": 720,
            "height": 1280,
            "duration": 30,
        },
        forward_origin={
            "type": "channel",
            "chat": {"id": channel, "type": "channel", "title": "channel"},
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


async def test_episode_post_is_stored_and_anime_sends_it_by_file_id(
    feed, settle, telegram, session_factory
):
    caption = "Токийский гуль 1 сезон 12. Призрак"
    await feed(forwarded("EP1", 30, channel=ANIME, caption=caption))

    async with session_factory() as session:
        (row,) = await session.scalars(select(AnimeEpisode))
    assert (row.season, row.episode, row.file_id) == (1, 12, "EP1")
    assert await edits(session_factory) == []

    await feed(message_update("/anime 1 12"))
    await settle()
    (video,) = telegram.bodies("sendVideo")
    assert video["video"] == "EP1"
    assert video["caption"] == only_text(Dialogs.anime.episode_caption(season=1, episode=12))


async def test_userbot_learns_the_last_stored_post_of_each_channel(feed, send):
    assert await send("/userbot_sync", uid=777) == []
    assert await send("/userbot_sync", uid=USERBOT) == ["userbot_sync {}"]

    for update in (
        forwarded("EDIT1", 10),
        forwarded("EDIT2", 12),
        forwarded("EDIT3", 11),
        forwarded("EP1", 30, channel=ANIME, caption="Токийский гуль 1 сезон 1. Трагедия"),
    ):
        await feed(update)

    (reply,) = await send("/userbot_sync", uid=USERBOT)
    assert reply == f"userbot_sync {json.dumps({str(CHANNEL): 12, str(ANIME): 30})}"
