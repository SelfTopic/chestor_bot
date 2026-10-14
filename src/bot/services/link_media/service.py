import asyncio
import logging
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...repositories import LinkMediaRepository
from ...types import CachedMedia
from ..ticker import Ticker
from .downloader import Slideshow, Video, run

logger = logging.getLogger(__name__)

TOOLS_UPDATE_INTERVAL = 24 * 3600
TOOLS = ("yt-dlp[default,curl-cffi]", "gallery-dl")


class MediaDownloader(Protocol):
    async def resolve(self, url: str) -> str: ...

    async def download(self, url: str, workdir: Path) -> Video | Slideshow: ...


class LinkMediaService:
    def __init__(
        self,
        downloader: MediaDownloader,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        enabled: bool,
        parallel: int = 2,
    ) -> None:
        self._downloader = downloader
        self._session_factory = session_factory
        self.enabled = enabled
        # Пачка ссылок в чат не должна разом занять весь канал и процессор сервера.
        self._slots = asyncio.Semaphore(parallel)

    async def resolve(self, url: str) -> str:
        return await self._downloader.resolve(url)

    # Свои сессии: кэш читают и пишут в after_handle, где сессии апдейта уже нет.
    async def cached(self, key: str) -> CachedMedia | None:
        async with self._session_factory() as session:
            return await LinkMediaRepository(session).get(key)

    async def remember(self, key: str, media: CachedMedia) -> None:
        async with self._session_factory() as session:
            await LinkMediaRepository(session).save(key, media)
            await session.commit()

    async def forget(self, key: str) -> None:
        async with self._session_factory() as session:
            await LinkMediaRepository(session).delete(key)
            await session.commit()

    @asynccontextmanager
    async def media(self, url: str) -> AsyncIterator[Video | Slideshow]:
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
