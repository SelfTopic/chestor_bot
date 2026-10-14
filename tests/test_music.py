"""«песня …»: поиск трека и отправка аудио по выбранной кнопке.

yt-dlp не запускается: вместо него — фейковый источник треков. Отправленное запоминается
в music_tracks по id трека и повторно уходит по file_id.
"""

from pathlib import Path
from typing import Any

import pytest

from src.bot.dialogs import Dialogs
from src.bot.services.music import Audio, MusicService, Track

from .conftest import button_data, callback_update, message_update, only_text, phrase_texts

MUSIC = Dialogs.music
UNRAVEL = Track(id="mtawrvojDyU", title="unravel", author="TK", duration=244)


class FakeSource:
    def __init__(self) -> None:
        self.tracks = [UNRAVEL]
        self.downloads: list[str] = []

    async def search(self, query: str) -> list[Track]:
        return self.tracks

    async def download(self, track_id: str, workdir: Path) -> Audio:
        self.downloads.append(track_id)
        path = workdir / "audio.m4a"
        path.write_bytes(b"m4a")
        return Audio(path, title="unravel", performer="TK", duration=244, thumbnail=None)


@pytest.fixture
def source(dispatcher, session_factory) -> FakeSource:
    fake = FakeSource()
    dispatcher.music_service = MusicService(fake, session_factory, enabled=True)
    return fake


def audio_message(file_id: str) -> dict[str, Any]:
    audio = {"file_id": file_id, "file_unique_id": "u", "duration": 244}
    return {"message_id": 100, "date": 5, "chat": {"id": 7, "type": "private"}, "audio": audio}


async def test_song_without_a_name_gets_usage(send, source):
    (reply,) = await send("песня")

    assert reply == only_text(MUSIC.usage())


async def test_unknown_song(feed, settle, telegram, source):
    source.tracks = []

    await feed(message_update("песня абвгд"))
    await settle()

    assert telegram.sent[0] in phrase_texts(MUSIC.not_found(query="абвгд"))


async def test_picked_track_is_sent_and_then_reused_by_file_id(
    feed, settle, telegram, source
):
    await feed(message_update("Песня unravel"))
    await settle()
    (results,) = telegram.bodies("sendMessage")
    assert results["text"] == only_text(MUSIC.results(query="unravel"))
    label = only_text(MUSIC.button(title="unravel", author="TK", duration="4:04"))
    pick = callback_update(button_data(results, label))

    telegram.results["sendAudio"] = audio_message("AUDIO")
    await feed(pick)
    await settle()

    (answer,) = telegram.bodies("answerCallbackQuery")
    assert answer["text"] == only_text(MUSIC.downloading())
    (sent,) = telegram.bodies("sendAudio")
    assert sent["audio"] == "<file:audio.m4a>"
    assert (sent["title"], sent["performer"], sent["duration"]) == ("unravel", "TK", "244")

    await feed(pick)
    await settle()

    (again,) = telegram.bodies("sendAudio")
    assert again["audio"] == "AUDIO"
    assert source.downloads == [UNRAVEL.id]
