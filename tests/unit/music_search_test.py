"""Запасной SoundCloud для «песня»: какая запись считается той же песней, и как из
метаданных достаются название и исполнитель."""

from src.bot.services.music.search import credits, soundcloud_candidates


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
