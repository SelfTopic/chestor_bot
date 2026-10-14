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


@dataclass(frozen=True)
class Video:
    path: Path
    width: int
    height: int
    duration: int
    thumbnail: Path | None


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
        self._limit = limit
        self._max_duration = max_duration

    async def download(self, url: str, workdir: Path) -> Video:
        async with aiohttp.ClientSession(
            headers={"User-Agent": BROWSER_UA}, timeout=aiohttp.ClientTimeout(total=60)
        ) as http:
            url = await self._resolve_short_link(url, http)
            try:
                return await self._ytdlp_video(url, workdir)
            except LinkMediaTooLarge:
                raise
            except LinkMediaError as exc:
                if "tiktok.com" not in url:
                    raise
                logger.warning("yt-dlp не скачал %s: %s; пробую tikwm", url, exc)

            try:
                return await self._tikwm_video(url, workdir, http)
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

    async def _ytdlp_video(self, url: str, workdir: Path) -> Video:
        info = await self._info(url)
        if not has_video(info):
            raise LinkMediaError(f"{url}: в посте нет видео")
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

    async def _tikwm_video(self, url: str, workdir: Path, http: aiohttp.ClientSession) -> Video:
        async with http.post(TIKWM_API, data={"url": url, "hd": "1"}) as response:
            response.raise_for_status()
            body = await response.json(content_type=None)
        if not isinstance(body, dict) or body.get("code") != 0:
            raise LinkMediaError(f"tikwm: {body.get('msg') if isinstance(body, dict) else body}")
        data = body["data"]
        source = data.get("hdplay") or data.get("play")
        if not source:
            raise LinkMediaError("tikwm: в посте нет видео")
        if source.startswith("/"):
            source = "https://www.tikwm.com" + source

        path = workdir / "tikwm.mp4"
        async with http.get(source) as response:
            response.raise_for_status()
            with path.open("wb") as file:
                async for chunk in response.content.iter_chunked(1 << 16):
                    file.write(chunk)
        return await self._checked(path, workdir)

    async def _checked(self, path: Path, workdir: Path) -> Video:
        if path.stat().st_size > self._limit:
            raise LinkMediaTooLarge()
        return await probe(path, workdir)


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
