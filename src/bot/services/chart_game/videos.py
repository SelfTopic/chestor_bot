import asyncio
import itertools
import logging
import multiprocessing
import os
from collections.abc import Callable, Iterable
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.config import game_config
from src.bot.repositories import ChartRepository

from .crash_video import crash_picture, crash_video_path, render_crash_video
from .growth_video import GROWTH_VIDEO

logger = logging.getLogger(__name__)

# Сначала то, что нужно раунду, потом прогрев частых значений.
URGENT, WARM = 0, 1
WARM_CRASHES = (range(100, 301), range(301, 501))


@dataclass(frozen=True)
class StoredVideo:
    key: str
    file_id: str


@dataclass(frozen=True)
class VideoFile:
    key: str
    path: Path


@dataclass(frozen=True)
class Picture:
    png: bytes


Media = StoredVideo | VideoFile | Picture


def _lower_priority() -> None:
    os.nice(10)


def _render_pool() -> Executor:
    # fork из процесса с потоками может зависнуть в дочернем процессе.
    return ProcessPoolExecutor(1, multiprocessing.get_context("spawn"), _lower_priority)


def video_key(path: Path) -> str:
    assets = Path(game_config.path_to_assets)
    name = path.relative_to(assets) if path.is_relative_to(assets) else path
    return f"{name}@{path.stat().st_mtime_ns}"


class ChartVideos:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        growth: Path = GROWTH_VIDEO,
        crash_path: Callable[[int], Path] = crash_video_path,
        render: Callable[[Path, int], None] = render_crash_video,
        executor: Callable[[], Executor] = _render_pool,
        warm: Iterable[range] = WARM_CRASHES,
    ) -> None:
        self._session_factory = session_factory
        self._growth = growth
        self._crash_path = crash_path
        self._render = render
        self._executor_factory = executor
        self._warm = warm
        self._queue: asyncio.PriorityQueue[tuple[int, int, int]] = asyncio.PriorityQueue()
        self._order = itertools.count()
        self._worker: asyncio.Task[None] | None = None
        self._executor: Executor | None = None

    def start(self) -> None:
        for crash in itertools.chain.from_iterable(self._warm):
            self._put(WARM, crash)
        self._executor = self._executor_factory()
        self._worker = asyncio.create_task(self._work())

    async def close(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)

    def request(self, crash: int) -> None:
        if not self._crash_path(crash).exists():
            self._put(URGENT, crash)

    async def idle(self) -> None:
        await self._queue.join()

    @property
    def ready(self) -> bool:
        return self._growth.exists()

    async def growth(self) -> Media:
        return await self._media(self._growth)

    async def crash(self, crash: int) -> Media:
        path = self._crash_path(crash)
        if not path.exists():
            return Picture(await asyncio.to_thread(crash_picture, crash))
        return await self._media(path)

    async def remember(self, video: VideoFile, file_id: str) -> None:
        async with self._session_factory() as session:
            await ChartRepository(session).save_video(video.key, file_id)
            await session.commit()

    async def forget(self, video: StoredVideo) -> None:
        async with self._session_factory() as session:
            await ChartRepository(session).forget_video(video.key)
            await session.commit()

    async def _media(self, path: Path) -> Media:
        key = video_key(path)
        async with self._session_factory() as session:
            file_id = await ChartRepository(session).video(key)
        return VideoFile(key, path) if file_id is None else StoredVideo(key, file_id)

    def _put(self, priority: int, crash: int) -> None:
        self._queue.put_nowait((priority, next(self._order), crash))

    async def _work(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            _, _, crash = await self._queue.get()
            try:
                path = self._crash_path(crash)
                if not path.exists():
                    await loop.run_in_executor(self._executor, self._render, path, crash)
            except Exception:
                logger.exception("Не отрендерился ролик обвала x%.2f", crash / 100)
            finally:
                self._queue.task_done()
