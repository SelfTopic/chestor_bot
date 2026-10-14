import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from src.bot.exceptions import LinkMediaError, LinkMediaTooLarge

from .formats import has_video, pick

logger = logging.getLogger(__name__)

TOOL_TIMEOUT = 180
TIKWM_API = "https://www.tikwm.com/api/"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
# --xff US обходит региональные блокировки постов TikTok с IP в Нидерландах.
YTDLP_FLAGS = ("--no-warnings", "--no-playlist", "--xff", "US")
# Обход через --xff срабатывает не каждый раз, поэтому при блокировке по IP повторяем.
GEO_BLOCK_ATTEMPTS = 3
GALLERY_FILE = 3


@dataclass(frozen=True)
class Video:
    path: Path
    width: int
    height: int
    duration: int
    thumbnail: Path | None


# Картинки слайдшоу — ссылками: Telegram скачивает их сам, а альбом из файлов с диска
# selfrot отправить не умеет.
@dataclass(frozen=True)
class Slideshow:
    images: tuple[str, ...]
    audio: Path | None


async def run(*args: str, timeout: float = TOOL_TIMEOUT) -> str:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        out, err = await asyncio.wait_for(process.communicate(), timeout)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise LinkMediaError(f"timeout: {' '.join(args[:3])}") from None
    if process.returncode != 0:
        lines = err.decode(errors="replace").strip().splitlines()
        raise LinkMediaError(lines[-1] if lines else f"exit code {process.returncode}")
    return out.decode(errors="replace")


class Downloader:
    def __init__(self, tools: Path, limit: int, max_duration: int) -> None:
        self._ytdlp = str(tools / "yt-dlp")
        self._gallerydl = str(tools / "gallery-dl")
        self._limit = limit
        self._max_duration = max_duration

    async def download(self, url: str, workdir: Path) -> Video | Slideshow:
        async with aiohttp.ClientSession(
            headers={"User-Agent": BROWSER_UA}, timeout=aiohttp.ClientTimeout(total=60)
        ) as http:
            url = await self._resolve_short_link(url, http)
            try:
                if "/photo/" in url:
                    return await self._slideshow(url, workdir, http)
                info = await self._info(url)
                if not has_video(info):
                    page = info.get("webpage_url")
                    return await self._slideshow(
                        page if isinstance(page, str) else url, workdir, http, info
                    )
                return await self._ytdlp_video(info, workdir)
            except LinkMediaTooLarge:
                raise
            except LinkMediaError as exc:
                if "tiktok.com" not in url:
                    raise
                logger.warning("yt-dlp не скачал %s: %s; пробую tikwm", url, exc)

            try:
                return await self._tikwm(url, workdir, http)
            except (aiohttp.ClientError, TimeoutError, ValueError, KeyError) as exc:
                raise LinkMediaError(f"tikwm не скачал {url}: {exc}") from exc

    async def _resolve_short_link(self, url: str, http: aiohttp.ClientSession) -> str:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if not (host.startswith(("vm.", "vt.")) or parts.path.startswith("/t/")):
            return url
        try:
            async with http.get(url) as response:
                return str(response.url)
        except (aiohttp.ClientError, TimeoutError) as exc:
            logger.warning("Короткая ссылка %s не раскрылась: %s", url, exc)
            return url

    async def _info(self, url: str) -> dict[str, Any]:
        for attempt in range(1, GEO_BLOCK_ATTEMPTS + 1):
            try:
                info = json.loads(await run(self._ytdlp, *YTDLP_FLAGS, "--dump-single-json", url))
            except LinkMediaError as exc:
                if "IP address is blocked" not in str(exc) or attempt == GEO_BLOCK_ATTEMPTS:
                    raise
                logger.info("Гео-блок для %s, попытка %d", url, attempt)
                continue
            if not isinstance(info, dict):
                raise LinkMediaError(f"yt-dlp: неожиданный ответ для {url}")
            return info
        raise AssertionError("unreachable")

    async def _ytdlp_video(self, info: dict[str, Any], workdir: Path) -> Video:
        duration = info.get("duration")
        if isinstance(duration, (int, float)) and duration > self._max_duration:
            raise LinkMediaTooLarge()
        choice = pick(info, self._limit)
        if choice is None:
            raise LinkMediaTooLarge()

        info_path = workdir / "info.json"
        info_path.write_text(json.dumps(info))
        out = await run(
            self._ytdlp,
            *YTDLP_FLAGS,
            "-f",
            choice.selector,
            "--merge-output-format",
            "mp4",
            "--load-info-json",
            str(info_path),
            "-o",
            str(workdir / "video.%(ext)s"),
            "--print",
            "after_move:filepath",
        )
        return await self._checked(Path(out.strip().splitlines()[-1]), workdir)

    async def _slideshow(
        self,
        url: str,
        workdir: Path,
        http: aiohttp.ClientSession,
        info: dict[str, Any] | None = None,
    ) -> Slideshow:
        files = _gallery_files(await run(self._gallerydl, "--quiet", "--dump-json", url))
        images = tuple(link for link, kind in files if kind == "image")
        if not images:
            raise LinkMediaError(f"gallery-dl: в {url} нет картинок")

        sound = next((link for link, kind in files if kind == "audio"), None)
        if sound is not None:
            audio: Path | None = await _fetch(http, sound, workdir / "audio.mp3")
        elif info is not None:
            audio = await self._ytdlp_audio(info, workdir)
        else:
            audio = None
        return Slideshow(images, audio)

    async def _ytdlp_audio(self, info: dict[str, Any], workdir: Path) -> Path | None:
        info_path = workdir / "info.json"
        info_path.write_text(json.dumps(info))
        try:
            out = await run(
                self._ytdlp,
                *YTDLP_FLAGS,
                "-f",
                "ba",
                "--load-info-json",
                str(info_path),
                "-o",
                str(workdir / "audio.%(ext)s"),
                "--print",
                "after_move:filepath",
            )
        except LinkMediaError as exc:
            logger.warning("Звук слайдшоу не скачался: %s", exc)
            return None
        return Path(out.strip().splitlines()[-1])

    async def _tikwm(
        self, url: str, workdir: Path, http: aiohttp.ClientSession
    ) -> Video | Slideshow:
        async with http.post(TIKWM_API, data={"url": url, "hd": "1"}) as response:
            response.raise_for_status()
            body = await response.json(content_type=None)
        if not isinstance(body, dict) or body.get("code") != 0:
            raise LinkMediaError(f"tikwm: {body.get('msg') if isinstance(body, dict) else body}")
        data = body["data"]

        images = data.get("images")
        if isinstance(images, list) and images:
            music = data.get("music")
            audio = await _fetch(http, _tikwm_url(music), workdir / "audio.mp3") if music else None
            return Slideshow(tuple(_tikwm_url(image) for image in images), audio)

        source = data.get("hdplay") or data.get("play")
        if not source:
            raise LinkMediaError("tikwm: в посте нет ни видео, ни картинок")
        path = await _fetch(http, _tikwm_url(source), workdir / "tikwm.mp4")
        return await self._checked(path, workdir)

    async def _checked(self, path: Path, workdir: Path) -> Video:
        if path.stat().st_size > self._limit:
            raise LinkMediaTooLarge()
        return await probe(path, workdir)


# Вывод gallery-dl --dump-json: список сообщений, файл — [3, ссылка, метаданные с type].
def _gallery_files(out: str) -> list[tuple[str, str]]:
    try:
        messages = json.loads(out)
    except ValueError as exc:
        raise LinkMediaError(f"gallery-dl: неожиданный вывод {out[:200]}") from exc
    if not isinstance(messages, list):
        raise LinkMediaError(f"gallery-dl: неожиданный вывод {out[:200]}")
    return [
        (message[1], str(message[2].get("type") or ""))
        for message in messages
        if isinstance(message, list)
        and len(message) >= 3
        and message[0] == GALLERY_FILE
        and isinstance(message[1], str)
        and isinstance(message[2], dict)
    ]


def _tikwm_url(link: str) -> str:
    return "https://www.tikwm.com" + link if link.startswith("/") else link


async def _fetch(http: aiohttp.ClientSession, url: str, path: Path) -> Path:
    async with http.get(url) as response:
        response.raise_for_status()
        with path.open("wb") as file:
            async for chunk in response.content.iter_chunked(1 << 16):
                file.write(chunk)
    return path


async def probe(path: Path, workdir: Path) -> Video:
    out = await run(
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path),
    )  # fmt: skip
    meta = json.loads(out)
    stream = (meta.get("streams") or [{}])[0]
    duration = float(meta.get("format", {}).get("duration") or 0)

    thumbnail: Path | None = workdir / "thumb.jpg"
    try:
        await run(
            "ffmpeg", "-v", "error", "-y", "-i", str(path), "-frames:v", "1",
            "-vf", "scale=320:320:force_original_aspect_ratio=decrease", str(thumbnail),
        )  # fmt: skip
    except LinkMediaError as exc:
        logger.warning("Превью для %s не сделалось: %s", path, exc)
        thumbnail = None

    return Video(
        path, int(stream.get("width") or 0), int(stream.get("height") or 0), round(duration), thumbnail
    )
