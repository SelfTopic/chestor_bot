import asyncio
import itertools
import logging
import multiprocessing
import os
from collections.abc import Callable, Iterable
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.config import game_config
from src.bot.repositories import ChartRepository

from .crash_video import UNLABELED_CRASH, crash_picture, crash_video_path, render_crash_video
from .growth_video import GROWTH_VIDEO
from .history import history_strip

logger = logging.getLogger(__name__)

# Сначала то, что нужно раунду, потом прогрев частых значений.
URGENT, WARM = 0, 1
WARM_CRASHES = (range(100, 301), range(301, 501))
# Telegram пускает в канал около 20 сообщений в минуту: прогрев оставляет место срочным загрузкам.
WARM_UPLOAD_GAP_SECONDS = 6.0
# Хостинг ограничивает сервер, если процессор долго занят больше чем на 70%: после каждого
# ролика прогрев отдыхает втрое дольше, чем рендерил, — около 6% сервера на 4 ядрах.
WARM_REST_FACTOR = 3.0


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
        warm_gap: float = WARM_UPLOAD_GAP_SECONDS,
        warm_rest: float = WARM_REST_FACTOR,
    ) -> None:
        self._session_factory = session_factory
        self._growth = growth
        self._crash_path = crash_path
        self._render = render
        self._executor_factory = executor
        self._warm = warm
        self._warm_gap = warm_gap
        self._warm_rest = warm_rest
        # Без загрузчика файлы уходят прямо в правке сообщения.
        self.uploader: Uploader | None = None
        self._unlabeled: StoredPicture | None = None
        # Картинка обвала с числом — на случай, если ролик к обвалу не успеет.
        self._pictures: dict[int, StoredPicture] = {}
        self._picture_tasks: set[asyncio.Task[None]] = set()
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
        tasks = [*self._picture_tasks, *([self._worker] if self._worker else [])]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)

    def request(self, crash: int) -> None:
        self._put(URGENT, crash)
        if self.uploader is not None and crash not in self._pictures:
            task = asyncio.create_task(self._prepare_picture(crash))
            self._picture_tasks.add(task)
            task.add_done_callback(self._picture_tasks.discard)

    async def idle(self) -> None:
        await self._queue.join()
        await asyncio.gather(*self._picture_tasks, return_exceptions=True)

    @property
    def ready(self) -> bool:
        return self._growth.exists()

    async def growth(self) -> Media:
        return await self._media(self._growth)

    async def crash(self, crash: int) -> Media:
        path = self._crash_path(crash)
        if path.exists():
            media = await self._media(path)
            if isinstance(media, StoredVideo) or self.uploader is None:
                return media
        if (picture := self._pictures.get(crash)) is not None:
            return picture
        return await self.unlabeled(crash)

    async def unlabeled(self, crash: int) -> Media:
        if self._unlabeled is not None:
            return self._unlabeled
        return Picture(await asyncio.to_thread(crash_picture, crash))

    # Замена медиа, чей file_id Telegram отверг: файл, который правка загрузит сама.
    async def fresh(self, media: Media, crash: int | None) -> Media:
        if crash is None and isinstance(media, StoredVideo):
            return VideoFile(media.key, self._growth)
        if crash is None:
            return media
        return Picture(await asyncio.to_thread(crash_picture, crash))

    async def history(self, crashes: list[int]) -> Media:
        return await self.picture(await asyncio.to_thread(history_strip, crashes))

    async def picture(self, png: bytes) -> Media:
        if self.uploader is None:
            return Picture(png)
        return StoredPicture(await self.uploader.picture(png))

    async def remember(self, video: VideoFile, file_id: str) -> None:
        async with self._session_factory() as session:
            await ChartRepository(session).save_video(video.key, file_id)
            await session.commit()

    async def forget(self, video: StoredVideo) -> None:
        async with self._session_factory() as session:
            await ChartRepository(session).forget_video(video.key)
            await session.commit()

    async def _media(self, path: Path) -> StoredVideo | VideoFile:
        key = video_key(path)
        async with self._session_factory() as session:
            file_id = await ChartRepository(session).video(key)
        return VideoFile(key, path) if file_id is None else StoredVideo(key, file_id)

    def _put(self, priority: int, crash: int) -> None:
        self._queue.put_nowait((priority, next(self._order), crash))

    async def _work(self) -> None:
        await self._prepare_shared()
        loop = asyncio.get_running_loop()
        while True:
            priority, _, crash = await self._queue.get()
            try:
                path = self._crash_path(crash)
                rest = 0.0
                if not path.exists():
                    started = loop.time()
                    await loop.run_in_executor(self._executor, self._render, path, crash)
                    rest = (loop.time() - started) * self._warm_rest
                if await self._upload(path):
                    rest = max(rest, self._warm_gap)
                if priority == WARM:
                    await asyncio.sleep(rest)
            except Exception:
                logger.exception("Ролик обвала x%.2f не подготовлен", crash / 100)
            finally:
                self._queue.task_done()

    async def _prepare_picture(self, crash: int) -> None:
        assert self.uploader is not None
        try:
            png = await asyncio.to_thread(crash_picture, crash)
            self._pictures[crash] = StoredPicture(await self.uploader.picture(png))
        except Exception:
            logger.exception("Картинка обвала x%.2f не загрузилась", crash / 100)

    async def _prepare_shared(self) -> None:
        if self.uploader is None:
            return
        try:
            png = await asyncio.to_thread(crash_picture, UNLABELED_CRASH, False)
            self._unlabeled = StoredPicture(await self.uploader.picture(png))
            if self.ready:
                await self._upload(self._growth)
        except Exception:
            logger.exception("Общие ролики «Джета» не загрузились")

    async def _upload(self, path: Path) -> bool:
        if self.uploader is None:
            return False
        media = await self._media(path)
        if isinstance(media, StoredVideo):
            return False
        await self.remember(media, await self.uploader.video(path))
        return True
