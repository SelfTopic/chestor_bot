import json
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.bot.exceptions import MediaToolError, MusicError

from ..media_tools import YTDLP_FLAGS, run

logger = logging.getLogger(__name__)

RESULTS = 5
# Канал автозагрузок YouTube Music называется «Исполнитель - Topic».
TOPIC_SUFFIX = " - Topic"
# YouTube душит скачивание с IP сервера (403 или зависание), а поиск при этом работает:
# долго ждать нет смысла, лучше сразу к SoundCloud.
YOUTUBE_TIMEOUT = 60
SOUNDCLOUD_RESULTS = 6
# Без подписки Go+ SoundCloud отдаёт вместо трека превью ровно на 30 секунд.
PREVIEW_SECONDS = 31
# Та же песня на SoundCloud — запись почти той же длины, а не кавер или нарезка.
SAME_SONG_SECONDS = 15
# Часть записей SoundCloud под DRM: их yt-dlp не скачает, берётся следующая по близости.
SOUNDCLOUD_TRIES = 3
SEEN_TRACKS = 2000
NOISE = re.compile(
    r"[\(\[【].*?[\)\]】]|[『』「」]|\b(?:official|music|lyrics?|video|audio|mv|hd|4k)\b",
    re.IGNORECASE,
)


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
        # Что показывали в поиске: по этому при отказе YouTube ищется та же песня на SoundCloud.
        self._seen: OrderedDict[str, Track] = OrderedDict()

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
        found = [track for track in tracks if track.duration <= self._max_duration][:RESULTS]
        for track in found:
            self._seen[track.id] = track
            self._seen.move_to_end(track.id)
        while len(self._seen) > SEEN_TRACKS:
            self._seen.popitem(last=False)
        return found

    async def download(self, track_id: str, workdir: Path) -> Audio:
        try:
            return await self._fetch(
                f"https://www.youtube.com/watch?v={track_id}",
                workdir / "youtube",
                ("-f", "bestaudio[ext=m4a]/bestaudio"),
                timeout=YOUTUBE_TIMEOUT,
            )
        except MediaToolError as exc:
            track = self._seen.get(track_id)
            if track is None:
                raise
            logger.warning("YouTube не отдал %s (%s), ищу на SoundCloud", track_id, exc)
            return await self._soundcloud(track, workdir)

    async def _soundcloud(self, track: Track, workdir: Path) -> Audio:
        urls = await self._soundcloud_urls(track)
        for attempt, url in enumerate(urls[:SOUNDCLOUD_TRIES]):
            try:
                return await self._fetch(
                    url,
                    workdir / f"soundcloud{attempt}",
                    ("-f", "bestaudio[ext=mp3]/bestaudio", "-x", "--audio-format", "mp3"),
                )
            except MediaToolError as exc:
                logger.info("SoundCloud не отдал %s: %s", url, exc)
        raise MusicError(f"SoundCloud: ни одна запись «{track.title}» не скачалась")

    async def _soundcloud_urls(self, track: Track) -> list[str]:
        query = " ".join(f"{track.author} {NOISE.sub(' ', track.title)}".split())
        out = await run(
            self._ytdlp,
            *YTDLP_FLAGS,
            "--flat-playlist",
            "--dump-single-json",
            f"scsearch{SOUNDCLOUD_RESULTS}:{query}",
        )
        urls = soundcloud_candidates(_entries(out), track.duration)
        if not urls:
            raise MusicError(f"SoundCloud: нет полной записи для «{query}»")
        return urls

    async def _fetch(
        self, url: str, workdir: Path, format_flags: tuple[str, ...], *, timeout: float = 180
    ) -> Audio:
        workdir.mkdir()
        out = await run(
            self._ytdlp,
            *YTDLP_FLAGS,
            *format_flags,
            "--write-thumbnail",
            "--convert-thumbnails",
            "jpg",
            "-o",
            str(workdir / "audio.%(ext)s"),
            "--print",
            "after_move:filepath",
            "--print",
            "after_move:%(.{track,artist,title,channel,uploader,duration})j",
            url,
            timeout=timeout,
        )
        lines = out.strip().splitlines()
        if len(lines) < 2:
            raise MusicError(f"yt-dlp: неожиданный вывод для {url}")
        meta = json.loads(lines[-1])
        path = Path(lines[-2])
        if not isinstance(meta, dict):
            raise MusicError(f"yt-dlp: неожиданные метаданные для {url}")
        if (meta.get("duration") or 0) > self._max_duration:
            raise MusicError(f"{url}: длиннее {self._max_duration} с")

        title, performer = credits(meta)
        return Audio(
            path=path,
            title=title,
            performer=performer,
            duration=int(meta.get("duration") or 0),
            thumbnail=await _thumbnail(workdir),
        )


# Без поля artist (так у загрузок фанатов) исполнитель часто стоит в названии «Кино - Песня»,
# а загрузивший — случайный человек.
def credits(meta: dict[str, Any]) -> tuple[str, str]:
    title = str(meta.get("track") or meta.get("title") or "")
    if meta.get("artist"):
        return title, str(meta["artist"])
    artist, dash, song = title.partition(" - ")
    if dash and artist and song:
        return song, artist
    return title, _author(meta.get("channel") or meta.get("uploader"))


def soundcloud_candidates(entries: list[dict[str, Any]], duration: int) -> list[str]:
    full = [
        (abs(entry_duration - duration), url)
        for entry in entries
        if isinstance(url := entry.get("url"), str)
        and isinstance(entry_duration := entry.get("duration"), (int, float))
        and entry_duration > PREVIEW_SECONDS
        and abs(entry_duration - duration) <= SAME_SONG_SECONDS
    ]
    return [url for _, url in sorted(full)]


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
