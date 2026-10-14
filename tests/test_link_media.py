"""Медиа по ссылке TikTok/YouTube: бот отвечает на сообщение роликом или фотокаруселью.

yt-dlp не запускается: вместо загрузчика — фейк, который кладёт файл в рабочую папку.
Отправленное запоминается в link_media_cache по id поста и повторно уходит по file_id.
"""

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from src.bot.dialogs import Dialogs
from src.bot.exceptions import LinkMediaError, LinkMediaTooLarge
from src.bot.repositories import LinkMediaRepository
from src.bot.services.link_media import LinkMediaService, Slideshow, Video
from src.bot.types import CachedSlideshow, CachedVideo
from src.database.models import LinkMediaCache

from .conftest import message_update, phrase_texts

SHORT = "https://vt.tiktok.com/ZSbYQSbFS/"
POST = "https://www.tiktok.com/@user/video/7412345678901234567"
KEY = "tiktok:7412345678901234567"


class FakeDownloader:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.error: Exception | None = None
        self.images: tuple[str, ...] = ()

    async def resolve(self, url: str) -> str:
        return POST if url == SHORT else url

    async def download(self, url: str, workdir: Path) -> Video | Slideshow:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        if self.images:
            return Slideshow(self.images, "https://cdn.example/sound.mp3")
        path = workdir / "video.mp4"
        path.write_bytes(b"mp4")
        return Video(path, width=720, height=1280, duration=12, thumbnail=None)


@pytest.fixture
def downloader(dispatcher, session_factory) -> FakeDownloader:
    fake = FakeDownloader()
    dispatcher.link_media_service = LinkMediaService(fake, session_factory, enabled=True)
    return fake


def sent_message(**media: Any) -> dict[str, Any]:
    return {"message_id": 100, "date": 5, "chat": {"id": 7, "type": "private"}, **media}


def video_message(file_id: str) -> dict[str, Any]:
    video = {"file_id": file_id, "file_unique_id": "u", "width": 1, "height": 1, "duration": 1}
    return sent_message(video=video)


def photo(file_id: str) -> dict[str, Any]:
    size = {"file_id": file_id, "file_unique_id": f"u{file_id}", "width": 1, "height": 1}
    return {"type": "photo", "photo": [size]}


async def cached(session_factory) -> dict[str, Any]:
    async with session_factory() as session:
        rows = await session.scalars(select(LinkMediaCache))
        return {row.key: row for row in rows}


async def test_link_anywhere_in_the_text_gets_the_video_and_is_cached(
    feed, settle, telegram, downloader, session_factory
):
    telegram.results["sendVideo"] = video_message("VIDEO")

    await feed(message_update(f"ору {SHORT} 😂"))
    await settle()

    assert downloader.urls == [POST]
    assert [b["action"] for b in telegram.bodies("sendChatAction")] == ["upload_video"]
    (video,) = telegram.bodies("sendVideo")
    assert video["video"] == "<file:video.mp4>"
    assert (video["width"], video["height"], video["duration"]) == ("720", "1280", "12")
    assert "reply_parameters" in video
    assert (await cached(session_factory))[KEY].video_file_id == "VIDEO"


async def test_cached_post_is_sent_by_file_id_for_any_form_of_the_link(
    feed, settle, telegram, downloader, session_factory
):
    async with session_factory() as session:
        await LinkMediaRepository(session).save(KEY, CachedVideo("VIDEO"))
        await session.commit()

    await feed(message_update(f"{POST}?lang=ru"))
    await settle()

    assert downloader.urls == []
    (video,) = telegram.bodies("sendVideo")
    assert video["video"] == "VIDEO"


async def test_stale_file_id_is_replaced_by_a_fresh_upload(
    feed, settle, telegram, downloader, session_factory
):
    async with session_factory() as session:
        await LinkMediaRepository(session).save(KEY, CachedVideo("OLD"))
        await session.commit()
    telegram.fail_next("sendVideo", "video", "OLD")
    telegram.results["sendVideo"] = video_message("NEW")

    await feed(message_update(SHORT))
    await settle()

    assert downloader.urls == [POST]
    assert [b["video"] for b in telegram.bodies("sendVideo")] == ["OLD", "<file:video.mp4>"]
    assert (await cached(session_factory))[KEY].video_file_id == "NEW"


async def test_slideshow_is_one_rich_message_with_photos_and_sound(
    feed, settle, telegram, downloader, session_factory
):
    downloader.images = ("https://cdn.example/1.jpeg", "https://cdn.example/2.jpeg")
    audio = {"file_id": "SOUND", "file_unique_id": "us", "duration": 9}
    telegram.results["sendRichMessage"] = sent_message(
        rich_message={
            "blocks": [
                {"type": "slideshow", "blocks": [photo("P1"), photo("P2")]},
                {"type": "audio", "audio": audio},
            ]
        }
    )

    await feed(message_update(SHORT))
    await settle()

    (body,) = telegram.bodies("sendRichMessage")
    slideshow, sound = body["rich_message"]["blocks"]
    assert [b["photo"]["media"] for b in slideshow["blocks"]] == list(downloader.images)
    assert sound["audio"]["media"] == "https://cdn.example/sound.mp3"
    row = (await cached(session_factory))[KEY]
    assert (row.photo_file_ids, row.audio_file_id) == (["P1", "P2"], "SOUND")

    async with session_factory() as session:
        assert await LinkMediaRepository(session).get(KEY) == CachedSlideshow(
            ("P1", "P2"), "SOUND"
        )


async def test_too_large_video_is_explained(feed, settle, telegram, downloader):
    downloader.error = LinkMediaTooLarge()

    await feed(message_update(SHORT))
    await settle()

    assert telegram.bodies("sendVideo") == []
    (reply,) = telegram.sent
    assert reply in phrase_texts(Dialogs.link_media.too_large())


async def test_failed_download_stays_silent(feed, settle, telegram, downloader):
    downloader.error = LinkMediaError("yt-dlp: Unsupported URL")

    await feed(message_update(SHORT))
    await settle()

    assert telegram.bodies("sendVideo") == []
    assert telegram.sent == []


async def test_without_yt_dlp_links_are_ignored(feed, settle, telegram, dispatcher, session_factory):
    fake = FakeDownloader()
    dispatcher.link_media_service = LinkMediaService(fake, session_factory, enabled=False)

    await feed(message_update(SHORT))
    await settle()

    assert fake.urls == []
    assert telegram.calls == []
