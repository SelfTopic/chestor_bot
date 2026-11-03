import multiprocessing
import os
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.config import game_config
from src.bot.repositories import ArcadeVideoRepository


@dataclass(frozen=True)
class StoredVideo:
    key: str
    file_id: str


@dataclass(frozen=True)
class StoredPicture:
    file_id: str


@dataclass(frozen=True)
class VideoFile:
    key: str
    path: Path


@dataclass(frozen=True)
class Picture:
    png: bytes


Media = StoredVideo | StoredPicture | VideoFile | Picture


# Загружает файл в Telegram мимо игры и отдаёт его file_id.
class Uploader(Protocol):
    async def video(self, path: Path) -> str: ...

    async def picture(self, png: bytes) -> str: ...


def _lower_priority() -> None:
    os.nice(10)


def render_pool() -> Executor:
    # fork из процесса с потоками может зависнуть в дочернем процессе.
    return ProcessPoolExecutor(1, multiprocessing.get_context("spawn"), _lower_priority)


def video_key(path: Path) -> str:
    assets = Path(game_config.path_to_assets)
    name = path.relative_to(assets) if path.is_relative_to(assets) else path
    return f"{name}@{path.stat().st_mtime_ns}"


class VideoCache:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        # Без загрузчика файлы уходят прямо в правке сообщения.
        self.uploader: Uploader | None = None

    async def media(self, path: Path) -> StoredVideo | VideoFile:
        key = video_key(path)
        async with self._session_factory() as session:
            file_id = await ArcadeVideoRepository(session).file_id(key)
        return VideoFile(key, path) if file_id is None else StoredVideo(key, file_id)

    async def remember(self, video: VideoFile, file_id: str) -> None:
        async with self._session_factory() as session:
            await ArcadeVideoRepository(session).save(video.key, file_id)
            await session.commit()

    async def forget(self, video: StoredVideo) -> None:
        async with self._session_factory() as session:
            await ArcadeVideoRepository(session).forget(video.key)
            await session.commit()

    async def picture(self, png: bytes) -> Picture | StoredPicture:
        if self.uploader is None:
            return Picture(png)
        return StoredPicture(await self.uploader.picture(png))

    async def upload(self, path: Path) -> bool:
        if self.uploader is None:
            return False
        media = await self.media(path)
        if isinstance(media, StoredVideo):
            return False
        await self.remember(media, await self.uploader.video(path))
        return True
