"""«песня …» и «шазам»: поиск трека, распознавание песни из голосового, кружка или видео и
отправка аудио по выбранной кнопке.

yt-dlp и Shazam не запускаются: вместо них — фейки. Отправленное запоминается в music_tracks
по id трека и повторно уходит по file_id.
"""

from pathlib import Path
from typing import Any

import pytest

from src.bot.dialogs import Dialogs
from src.bot.services.music import Audio, MusicService, Recognized, Track

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


class FakeRecognizer:
    def __init__(self) -> None:
        self.song: Recognized | None = Recognized("Unravel", "TK")
        self.heard: list[bytes] = []

    async def recognize(self, source: Path, workdir: Path) -> Recognized | None:
        self.heard.append(source.read_bytes())
        return self.song


@pytest.fixture
def recognizer() -> FakeRecognizer:
    return FakeRecognizer()


@pytest.fixture
def source(dispatcher, session_factory, recognizer) -> FakeSource:
    fake = FakeSource()
    dispatcher.music_service = MusicService(fake, recognizer, session_factory, enabled=True)
    return fake


def audio_message(file_id: str) -> dict[str, Any]:
    audio = {"file_id": file_id, "file_unique_id": "u", "duration": 244}
    return {"message_id": 100, "date": 5, "chat": {"id": 7, "type": "private"}, "audio": audio}


@pytest.mark.parametrize("word", ["песня", "song"])
async def test_song_without_a_name_gets_usage(send, source, word):
    (reply,) = await send(word)

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


def reply_with(media: str, size: int = 1000) -> dict[str, Any]:
    body = {"file_id": "F", "file_unique_id": "uF", "duration": 9, "file_size": size}
    if media == "video_note":
        body["length"] = 240
    if media == "video":
        body |= {"width": 640, "height": 360}
    return message_update("шазам", reply_to_uid=8, reply_extra={media: body})


@pytest.mark.parametrize("media", ["voice", "video_note"])
async def test_shazam_names_the_song_and_offers_the_tracks(
    feed, settle, telegram, source, recognizer, media
):
    telegram.results["getFile"] = {"file_id": "F", "file_unique_id": "uF", "file_path": "f/1"}
    telegram.set_file("f/1", b"sound")

    await feed(reply_with(media))
    await settle()

    assert recognizer.heard == [b"sound"]
    (reply,) = telegram.bodies("sendMessage")
    assert reply["text"] == only_text(MUSIC.shazam.recognized(title="Unravel", artist="TK"))
    label = only_text(MUSIC.button(title="unravel", author="TK", duration="4:04"))
    assert button_data(reply, label)


async def test_shazam_needs_a_reply_to_sound(send, source):
    (reply,) = await send("шазам", reply_to_uid=8)

    assert reply == only_text(MUSIC.shazam.usage())


async def test_shazam_refuses_files_over_the_bot_download_limit(feed, telegram, source):
    await feed(reply_with("video", size=30 * 1024 * 1024))

    assert telegram.sent == [only_text(MUSIC.shazam.too_big())]
    assert telegram.bodies("getFile") == []


async def test_unknown_song_is_reported(feed, settle, telegram, source, recognizer):
    recognizer.song = None
    telegram.results["getFile"] = {"file_id": "F", "file_unique_id": "uF", "file_path": "f/1"}
    telegram.set_file("f/1", b"sound")

    await feed(reply_with("voice"))
    await settle()

    assert telegram.sent[0] in phrase_texts(MUSIC.shazam.not_recognized())
