import asyncio
import itertools
import logging
from collections.abc import Callable
from concurrent.futures import Executor
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..arcade.media import (
    Media,
    Picture,
    StoredPicture,
    StoredVideo,
    Uploader,
    VideoCache,
    VideoFile,
    render_pool,
    video_key,
)
from .positions import Clip, clips
from .spin_video import render_spin_video, rest_picture, spin_video_path

logger = logging.getLogger(__name__)

# Сначала ролик, которого не хватило прокруту, потом загрузка всех остальных.
URGENT, WARM = 0, 1
# Telegram пускает в канал около 20 сообщений в минуту: прогрев оставляет место срочным загрузкам.
WARM_UPLOAD_GAP_SECONDS = 6.0
# Релиза с набором может ещё не быть: GitHub рендерит его минут двадцать после пуша.
DOWNLOAD_RETRY_SECONDS = 600.0


class VideoSource(Protocol):
    @property
    def complete(self) -> bool: ...

    async def download(self) -> None: ...


class RouletteVideos:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        source: VideoSource | None = None,
        spin_path: Callable[[Clip], Path] = spin_video_path,
        render: Callable[[Clip, Path], Path] = render_spin_video,
        picture: Callable[[int], bytes] = rest_picture,
        executor: Callable[[], Executor] = render_pool,
        warm: bool = True,
        warm_gap: float = WARM_UPLOAD_GAP_SECONDS,
        retry: float = DOWNLOAD_RETRY_SECONDS,
    ) -> None:
        self._cache = VideoCache(session_factory)
        self._source = source
        self._spin_path = spin_path
        self._render = render
        self._picture = picture
        self._executor_factory = executor
        self._warm = warm
        self._warm_gap = warm_gap
        self._retry = retry
        self._rest: dict[int, StoredPicture] = {}
        self._queue: asyncio.PriorityQueue[tuple[int, int, Clip]] = asyncio.PriorityQueue()
        self._order = itertools.count()
        self._worker: asyncio.Task[None] | None = None
        self._fetcher: asyncio.Task[None] | None = None
        self._executor: Executor | None = None

    @property
    def uploader(self) -> Uploader | None:
        return self._cache.uploader

    @uploader.setter
    def uploader(self, uploader: Uploader | None) -> None:
        self._cache.uploader = uploader

    def start(self) -> None:
        self._executor = self._executor_factory()
        self._worker = asyncio.create_task(self._work())
        self._fetcher = asyncio.create_task(self._fetch())

    async def close(self) -> None:
        tasks = [task for task in (self._fetcher, self._worker) if task is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)

    async def idle(self) -> None:
        if self._fetcher is not None:
            await self._fetcher
        await self._queue.join()

    def ready(self, clip: Clip) -> bool:
        return self._spin_path(clip).exists()

    async def spin(self, clip: Clip) -> StoredVideo | VideoFile | None:
        path = self._spin_path(clip)
        if not path.exists():
            self._put(URGENT, clip)
            return None
        return await self._cache.media(path)

    async def rest(self, position: int) -> Media:
        if (stored := self._rest.get(position)) is not None:
            return stored
        png = await asyncio.to_thread(self._picture, position)
        if self.uploader is None:
            return Picture(png)
        # Картинка покоя приходит в каждой правке: загруженная один раз, она уходит по file_id.
        stored = StoredPicture(await self.uploader.picture(png))
        self._rest[position] = stored
        return stored

    async def picture(self, png: bytes) -> Media:
        return await self._cache.picture(png)

    # Замены медиа, чей file_id Telegram отверг: файл, который правка загрузит сама.
    async def fresh_spin(self, video: StoredVideo, clip: Clip) -> VideoFile:
        await self._cache.forget(video)
        path = self._spin_path(clip)
        return VideoFile(video_key(path), path)

    async def fresh_rest(self, position: int) -> Picture:
        self._rest.pop(position, None)
        return Picture(await asyncio.to_thread(self._picture, position))

    async def remember(self, video: VideoFile, file_id: str) -> None:
        await self._cache.remember(video, file_id)

    def _put(self, priority: int, clip: Clip) -> None:
        self._queue.put_nowait((priority, next(self._order), clip))

    async def _fetch(self) -> None:
        while self._source is not None and not self._source.complete:
            try:
                await self._source.download()
            except Exception:
                logger.warning("Набор роликов рулетки не скачался", exc_info=True)
                await asyncio.sleep(self._retry)
        if self._warm:
            for clip in clips():
                self._put(WARM, clip)

    async def _work(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            priority, _, clip = await self._queue.get()
            try:
                path = self._spin_path(clip)
                # Ролики рендерит GitHub: на сервере — только тот, которого не хватило прокруту.
                if not path.exists() and priority == URGENT:
                    await loop.run_in_executor(self._executor, self._render, clip, path)
                if path.exists() and await self._cache.upload(path) and priority == WARM:
                    await asyncio.sleep(self._warm_gap)
            except Exception:
                logger.exception("Ролик рулетки %s не подготовлен", clip)
            finally:
                self._queue.task_done()
