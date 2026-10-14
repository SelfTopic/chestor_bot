"""Запасной SoundCloud для «песня»: YouTube и SoundCloud качают наперегонки, какая запись
SoundCloud считается той же песней, как из метаданных достаются название и исполнитель."""

import asyncio
from pathlib import Path

import pytest

from src.bot.exceptions import MediaToolError, MusicError
from src.bot.services.music import Audio
from src.bot.services.music.search import credits, first_success, soundcloud_candidates


def entry(url: str, duration: float) -> dict[str, object]:
    return {"url": url, "duration": duration}


def test_previews_and_other_lengths_are_skipped_closest_first() -> None:
    entries = [
        entry("preview", 30.0),
        entry("parody", 236.7),
        entry("cover", 260.0),
        entry("full", 238.1),
    ]

    assert soundcloud_candidates(entries, 244) == ["full", "parody"]


def test_artist_comes_from_the_field_or_from_the_title() -> None:
    assert credits({"title": "Unravel", "artist": "TK"}) == ("Unravel", "TK")
    assert credits({"title": "Кино - Группа крови", "uploader": "fan"}) == ("Группа крови", "Кино")
    assert credits({"title": "unravel", "channel": "TK - Topic"}) == ("unravel", "TK")


def audio(name: str) -> Audio:
    return Audio(Path(name), title=name, performer="", duration=1, thumbnail=None)


async def fails(after: float) -> Audio:
    await asyncio.sleep(after)
    raise MediaToolError("HTTP Error 403: Forbidden")


async def succeeds(name: str, after: float, finished: list[str]) -> Audio:
    try:
        await asyncio.sleep(after)
    except asyncio.CancelledError:
        finished.append(f"{name} cancelled")
        raise
    return audio(name)


async def test_first_download_to_finish_wins_and_the_other_is_cancelled() -> None:
    finished: list[str] = []

    won = await first_success(
        succeeds("youtube", 0.01, finished), succeeds("soundcloud", 5, finished)
    )

    assert won.title == "youtube"
    assert finished == ["soundcloud cancelled"]


async def test_a_failed_source_leaves_the_race_to_the_other() -> None:
    won = await first_success(fails(0), succeeds("soundcloud", 0.02, []))

    assert won.title == "soundcloud"


async def test_both_failed_is_a_music_error() -> None:
    with pytest.raises(MusicError):
        await first_success(fails(0), fails(0.01))
