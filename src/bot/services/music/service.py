import asyncio
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...repositories import MusicTrackRepository
from .recognize import Recognized
from .search import Audio, Track


class TrackSource(Protocol):
    async def search(self, query: str) -> list[Track]: ...

    async def download(self, track_id: str, workdir: Path) -> Audio: ...


class SongRecognizer(Protocol):
    async def recognize(self, source: Path, workdir: Path) -> Recognized | None: ...


class MusicService:
    def __init__(
        self,
        finder: TrackSource,
        recognizer: SongRecognizer,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        enabled: bool,
        parallel: int = 2,
    ) -> None:
        self._finder = finder
        self._recognizer = recognizer
        self._session_factory = session_factory
        self.enabled = enabled
        self._slots = asyncio.Semaphore(parallel)

    async def search(self, query: str) -> list[Track]:
        return await self._finder.search(query)

    # Свои сессии: кэш читают и пишут в after_handle, где сессии апдейта уже нет.
    async def cached(self, track_id: str) -> str | None:
        async with self._session_factory() as session:
            return await MusicTrackRepository(session).file_id(track_id)

    async def remember(self, track_id: str, file_id: str) -> None:
        async with self._session_factory() as session:
            await MusicTrackRepository(session).save(track_id, file_id)
            await session.commit()

    async def forget(self, track_id: str) -> None:
        async with self._session_factory() as session:
            await MusicTrackRepository(session).delete(track_id)
            await session.commit()

    async def recognize(self, media: bytes) -> Recognized | None:
        async with self._slots:
            with tempfile.TemporaryDirectory(prefix="shazam_") as workdir:
                source = Path(workdir) / "media"
                source.write_bytes(media)
                return await self._recognizer.recognize(source, Path(workdir))

    @asynccontextmanager
    async def audio(self, track_id: str) -> AsyncIterator[Audio]:
        async with self._slots:
            with tempfile.TemporaryDirectory(prefix="music_") as workdir:
                yield await self._finder.download(track_id, Path(workdir))
