import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.bot.exceptions import MusicError

from ..media_tools import YTDLP_FLAGS, run

logger = logging.getLogger(__name__)

RESULTS = 5
# Канал автозагрузок YouTube Music называется «Исполнитель - Topic».
TOPIC_SUFFIX = " - Topic"


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    author: str
    duration: int


@dataclass(frozen=True)
class Audio:
    path: Path
    title: str
    performer: str
    duration: int
    thumbnail: Path | None


class MusicFinder:
    def __init__(self, tools: Path, max_duration: int) -> None:
        self._ytdlp = str(tools / "yt-dlp")
        self._max_duration = max_duration

    async def search(self, query: str) -> list[Track]:
        out = await run(
            self._ytdlp,
            *YTDLP_FLAGS,
            "--flat-playlist",
            "--dump-single-json",
            f"ytsearch{RESULTS * 2}:{query}",
        )
        entries = _entries(out)
        tracks = [track for track in map(_track, entries) if track is not None]
        return [track for track in tracks if track.duration <= self._max_duration][:RESULTS]

    async def download(self, track_id: str, workdir: Path) -> Audio:
        out = await run(
            self._ytdlp,
            *YTDLP_FLAGS,
            "-f",
            "bestaudio[ext=m4a]/bestaudio",
            "--write-thumbnail",
            "--convert-thumbnails",
            "jpg",
            "-o",
            str(workdir / "audio.%(ext)s"),
            "--print",
            "after_move:filepath",
            "--print",
            "after_move:%(.{track,artist,title,channel,duration})j",
            f"https://www.youtube.com/watch?v={track_id}",
        )
        lines = out.strip().splitlines()
        if len(lines) < 2:
            raise MusicError(f"yt-dlp: неожиданный вывод для {track_id}")
        meta = json.loads(lines[-1])
        path = Path(lines[-2])
        if not isinstance(meta, dict):
            raise MusicError(f"yt-dlp: неожиданные метаданные для {track_id}")
        if (meta.get("duration") or 0) > self._max_duration:
            raise MusicError(f"{track_id}: длиннее {self._max_duration} с")

        return Audio(
            path=path,
            title=str(meta.get("track") or meta.get("title") or ""),
            performer=str(meta.get("artist") or _author(meta.get("channel"))),
            duration=int(meta.get("duration") or 0),
            thumbnail=await _thumbnail(workdir),
        )


def _entries(out: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(out)
    except ValueError as exc:
        raise MusicError(f"yt-dlp: неожиданный вывод {out[:200]}") from exc
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _track(entry: dict[str, Any]) -> Track | None:
    track_id, duration = entry.get("id"), entry.get("duration")
    if not isinstance(track_id, str) or not isinstance(duration, (int, float)):
        return None
    return Track(
        id=track_id,
        title=str(entry.get("title") or ""),
        author=_author(entry.get("channel") or entry.get("uploader")),
        duration=int(duration),
    )


def _author(channel: object) -> str:
    return str(channel or "").removesuffix(TOPIC_SUFFIX)


# Обложку аудио Telegram принимает только JPEG до 320×320 и 200 КБ.
async def _thumbnail(workdir: Path) -> Path | None:
    source = workdir / "audio.jpg"
    if not source.exists():
        return None
    thumbnail = workdir / "thumb.jpg"
    try:
        await run(
            "ffmpeg", "-v", "error", "-y", "-i", str(source),
            "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=320:320", str(thumbnail),
        )  # fmt: skip
    except Exception as exc:
        logger.warning("Обложка трека не сделалась: %s", exc)
        return None
    return thumbnail
