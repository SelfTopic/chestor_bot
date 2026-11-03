import asyncio
import itertools
import logging
from collections.abc import Callable
from concurrent.futures import Executor
from pathlib import Path

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
from .positions import POSITIONS
from .spin_video import render_spin_video, rest_picture, spin_video_path

logger = logging.getLogger(__name__)

# Сначала ролик, которого не хватило прокруту, потом прогрев всех остальных.
URGENT, WARM = 0, 1
# Telegram пускает в канал около 20 сообщений в минуту: прогрев оставляет место срочным загрузкам.
WARM_UPLOAD_GAP_SECONDS = 6.0
# Хостинг ограничивает сервер, если процессор долго занят больше чем на 70%: после каждого
# ролика прогрев отдыхает втрое дольше, чем рендерил.
WARM_REST_FACTOR = 3.0

Pair = tuple[int, int]


class RouletteVideos:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        spin_path: Callable[[int, int], Path] = spin_video_path,
        render: Callable[[int, int, Path], Path] = render_spin_video,
        picture: Callable[[int], bytes] = rest_picture,
        executor: Callable[[], Executor] = render_pool,
        warm: bool = True,
        warm_gap: float = WARM_UPLOAD_GAP_SECONDS,
        warm_rest: float = WARM_REST_FACTOR,
    ) -> None:
        self._cache = VideoCache(session_factory)
        self._spin_path = spin_path
        self._render = render
        self._picture = picture
        self._executor_factory = executor
        self._warm = warm
        self._warm_gap = warm_gap
        self._warm_rest = warm_rest
        self._rest: dict[int, StoredPicture] = {}
        self._queue: asyncio.PriorityQueue[tuple[int, int, Pair]] = asyncio.PriorityQueue()
        self._order = itertools.count()
        self._worker: asyncio.Task[None] | None = None
        self._executor: Executor | None = None

    @property
    def uploader(self) -> Uploader | None:
        return self._cache.uploader

    @uploader.setter
    def uploader(self, uploader: Uploader | None) -> None:
        self._cache.uploader = uploader

    def start(self) -> None:
        if self._warm:
            for start in range(len(POSITIONS)):
                for end in range(len(POSITIONS)):
                    self._put(WARM, (start, end))
        self._executor = self._executor_factory()
        self._worker = asyncio.create_task(self._work())

    async def close(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)

    async def idle(self) -> None:
        await self._queue.join()

    def ready(self, start: int, end: int) -> bool:
        return self._spin_path(start, end).exists()

    async def spin(self, start: int, end: int) -> StoredVideo | VideoFile | None:
        path = self._spin_path(start, end)
        if not path.exists():
            self._put(URGENT, (start, end))
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
    async def fresh_spin(self, video: StoredVideo, start: int, end: int) -> VideoFile:
        await self._cache.forget(video)
        path = self._spin_path(start, end)
        return VideoFile(video_key(path), path)

    async def fresh_rest(self, position: int) -> Picture:
        self._rest.pop(position, None)
        return Picture(await asyncio.to_thread(self._picture, position))

    async def remember(self, video: VideoFile, file_id: str) -> None:
        await self._cache.remember(video, file_id)

    def _put(self, priority: int, pair: Pair) -> None:
        self._queue.put_nowait((priority, next(self._order), pair))

    async def _work(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            priority, _, (start, end) = await self._queue.get()
            try:
                path = self._spin_path(start, end)
                rest = 0.0
                if not path.exists():
                    started = loop.time()
                    await loop.run_in_executor(self._executor, self._render, start, end, path)
                    rest = (loop.time() - started) * self._warm_rest
                if await self._cache.upload(path):
                    rest = max(rest, self._warm_gap)
                if priority == WARM:
                    await asyncio.sleep(rest)
            except Exception:
                logger.exception("Ролик рулетки %s→%s не подготовлен", start, end)
            finally:
                self._queue.task_done()
