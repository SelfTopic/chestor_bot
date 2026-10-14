"""Видео по ссылке TikTok/YouTube: бот отвечает на сообщение скачанным роликом.

yt-dlp не запускается: вместо загрузчика — фейк, который кладёт файл в рабочую папку.
"""

from pathlib import Path

import pytest

from src.bot.dialogs import Dialogs
from src.bot.exceptions import LinkMediaError, LinkMediaTooLarge
from src.bot.services.link_media import LinkMediaService, Video

from .conftest import message_update, phrase_texts

LINK = "https://vt.tiktok.com/ZSbYQSbFS/"


class FakeDownloader:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.error: Exception | None = None

    async def download(self, url: str, workdir: Path) -> Video:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        path = workdir / "video.mp4"
        path.write_bytes(b"mp4")
        return Video(path, width=720, height=1280, duration=12, thumbnail=None)


@pytest.fixture
def downloader(dispatcher) -> FakeDownloader:
    fake = FakeDownloader()
    dispatcher.link_media_service = LinkMediaService(fake, enabled=True)
    return fake


async def test_link_anywhere_in_the_text_gets_the_video(feed, settle, telegram, downloader):
    await feed(message_update(f"ору {LINK} 😂"))
    await settle()

    assert downloader.urls == [LINK]
    assert [b["action"] for b in telegram.bodies("sendChatAction")] == ["upload_video"]
    (video,) = telegram.bodies("sendVideo")
    assert video["video"] == "<file:video.mp4>"
    assert (video["width"], video["height"], video["duration"]) == ("720", "1280", "12")
    assert "reply_parameters" in video


async def test_too_large_video_is_explained(feed, settle, telegram, downloader):
    downloader.error = LinkMediaTooLarge()

    await feed(message_update(LINK))
    await settle()

    assert telegram.bodies("sendVideo") == []
    (reply,) = telegram.sent
    assert reply in phrase_texts(Dialogs.link_media.too_large())


async def test_failed_download_stays_silent(feed, settle, telegram, downloader):
    downloader.error = LinkMediaError("yt-dlp: Unsupported URL")

    await feed(message_update(LINK))
    await settle()

    assert telegram.bodies("sendVideo") == []
    assert telegram.sent == []


async def test_without_yt_dlp_links_are_ignored(feed, settle, telegram, dispatcher):
    fake = FakeDownloader()
    dispatcher.link_media_service = LinkMediaService(fake, enabled=False)

    await feed(message_update(LINK))
    await settle()

    assert fake.urls == []
    assert telegram.calls == []
