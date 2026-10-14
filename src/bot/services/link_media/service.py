import asyncio
import logging
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from ..ticker import Ticker
from .downloader import Video, run

logger = logging.getLogger(__name__)

TOOLS_UPDATE_INTERVAL = 24 * 3600
TOOLS = ("yt-dlp[default,curl-cffi]", "gallery-dl")


class VideoDownloader(Protocol):
    async def download(self, url: str, workdir: Path) -> Video: ...


class LinkMediaService:
    def __init__(
        self, downloader: VideoDownloader, *, enabled: bool, parallel: int = 2
    ) -> None:
        self._downloader = downloader
        self.enabled = enabled
        # Пачка ссылок в чат не должна разом занять весь канал и процессор сервера.
        self._slots = asyncio.Semaphore(parallel)

    @asynccontextmanager
    async def video(self, url: str) -> AsyncIterator[Video]:
        async with self._slots:
            with tempfile.TemporaryDirectory(prefix="link_media_") as workdir:
                yield await self._downloader.download(url, Path(workdir))


# yt-dlp и gallery-dl живут в своём venv и обновляются в нём: сайты ломают скачивание
# чаще, чем выходит новый образ бота, а зависимости самого бота это не трогает.
class MediaToolsUpdater(Ticker):
    def __init__(self, tools: Path, interval_seconds: float = TOOLS_UPDATE_INTERVAL) -> None:
        super().__init__(interval_seconds)
        self._tools = tools

    async def tick(self) -> None:
        pip = str(self._tools / "pip")
        await run(pip, "install", "-q", "-U", *TOOLS, timeout=600)
        version = (await run(str(self._tools / "yt-dlp"), "--version")).strip()
        logger.info("yt-dlp и gallery-dl обновлены (yt-dlp %s)", version)
