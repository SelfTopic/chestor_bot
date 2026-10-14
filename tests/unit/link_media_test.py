"""Ссылки TikTok/YouTube в тексте и выбор формата yt-dlp, который влезает в лимит Bot API."""

import json
from typing import Any

import pytest

from src.bot.services.link_media import find_links, pick
from src.bot.services.link_media.downloader import _gallery_files

MB = 1024 * 1024


@pytest.mark.parametrize(
    ("text", "links"),
    [
        ("глянь https://vt.tiktok.com/ZSbYQSbFS/ ахах", ["https://vt.tiktok.com/ZSbYQSbFS/"]),
        (
            "https://www.tiktok.com/@user/video/7412345678901234567?lang=ru.",
            ["https://www.tiktok.com/@user/video/7412345678901234567?lang=ru"],
        ),
        ("(https://youtu.be/dQw4w9WgXcQ)", ["https://youtu.be/dQw4w9WgXcQ"]),
        (
            "https://m.youtube.com/watch?app=desktop&v=dQw4w9WgXcQ&t=10",
            ["https://m.youtube.com/watch?app=desktop&v=dQw4w9WgXcQ&t=10"],
        ),
        ("https://youtube.com/shorts/abcdefghijk", ["https://youtube.com/shorts/abcdefghijk"]),
        ("канал https://www.youtube.com/@channel и https://example.com", []),
    ],
)
def test_links_are_found_anywhere_in_the_text(text: str, links: list[str]) -> None:
    assert find_links(text) == links


def test_repeated_links_count_once_and_at_most_three() -> None:
    text = " ".join(f"https://youtu.be/{n}{n}{n}{n}{n}{n}{n}{n}{n}{n}{n}" for n in "abcd")

    assert find_links(f"https://youtu.be/aaaaaaaaaaa {text}") == [
        "https://youtu.be/aaaaaaaaaaa",
        "https://youtu.be/bbbbbbbbbbb",
        "https://youtu.be/ccccccccccc",
    ]


def fmt(format_id: str, **fields: Any) -> dict[str, Any]:
    return {"format_id": format_id, "vcodec": "none", "acodec": "none", **fields}


def test_best_height_that_fits_wins_and_h264_breaks_ties() -> None:
    info = {
        "formats": [
            fmt("1080", vcodec="avc1", acodec="aac", height=1080, filesize=80 * MB),
            fmt("720vp9", vcodec="vp9", acodec="opus", height=720, filesize=20 * MB),
            fmt("720avc", vcodec="avc1", acodec="aac", height=720, filesize=30 * MB),
            fmt("480", vcodec="avc1", acodec="aac", height=480, filesize=10 * MB),
        ]
    }

    choice = pick(info, 49 * MB)

    assert choice is not None and choice.selector == "720avc"


def test_watermarked_tiktok_version_is_never_picked() -> None:
    info = {
        "formats": [
            fmt("download", vcodec="h264", acodec="aac", height=1080, filesize=5 * MB),
            fmt("play", vcodec="h264", acodec="aac", height=720, filesize=4 * MB),
        ]
    }

    choice = pick(info, 49 * MB)

    assert choice is not None and choice.selector == "play"


def test_separate_video_is_merged_with_m4a_audio_within_the_limit() -> None:
    info = {
        "formats": [
            fmt("140", acodec="mp4a", ext="m4a", abr=128, filesize=4 * MB),
            fmt("251", acodec="opus", ext="webm", abr=160, filesize=5 * MB),
            fmt("137", vcodec="avc1", ext="mp4", height=1080, filesize=46 * MB),
            fmt("136", vcodec="avc1", ext="mp4", height=720, filesize=25 * MB),
        ]
    }

    choice = pick(info, 49 * MB)

    assert choice is not None
    assert (choice.selector, choice.size) == ("136+140", 29 * MB)


def test_nothing_fits_means_too_large() -> None:
    info = {"formats": [fmt("18", vcodec="avc1", acodec="aac", height=360, filesize=60 * MB)]}

    assert pick(info, 49 * MB) is None


def test_gallery_dl_files_are_told_apart_by_type() -> None:
    out = json.dumps(
        [
            [2, {"id": "7695451669710048520"}],
            [3, "https://p16.tiktokcdn-eu.com/photo.jpeg", {"type": "image", "num": 1}],
            [3, "https://v45.tiktokcdn-eu.com/video/tos/sound", {"type": "audio", "num": 0}],
        ]
    )

    assert _gallery_files(out) == [
        ("https://p16.tiktokcdn-eu.com/photo.jpeg", "image"),
        ("https://v45.tiktokcdn-eu.com/video/tos/sound", "audio"),
    ]
