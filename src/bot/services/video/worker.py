# src/bot/services/video/worker.py
import asyncio
import logging

from ...types.media import VideoCutJob
from .cutter import VideoCutterService

logger = logging.getLogger(__name__)


class VideoWorker:
    def __init__(
        self,
        cutter: VideoCutterService,
        workers_count: int = 2,
        max_queue_size: int = 100,
    ):
        """
        Инициализация воркера с асинхронной обработкой видео.

        Args:
            cutter: Сервис нарезки видео
            workers_count: Количество параллельных воркеров
            max_queue_size: Максимальный размер очереди
        """
        logger.info(f"Initializing VideoWorker with {workers_count} workers")
        self.cutter = cutter
        self.queue: asyncio.Queue[VideoCutJob] = asyncio.Queue(maxsize=max_queue_size)
        self.workers_count = workers_count
        self.tasks: list[asyncio.Task] = []
        self._is_running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Запускает воркеров"""
        if self._is_running:
            logger.warning("VideoWorker is already running")
            return

        logger.info(f"Starting VideoWorker with {self.workers_count} workers")
        self._is_running = True
        self._shutdown_event.clear()

        self.tasks = [
            asyncio.create_task(self._worker(i)) for i in range(self.workers_count)
        ]

    async def enqueue(self, job: VideoCutJob) -> None:
        """
        Добавляет задачу в очередь.

        Raises:
            asyncio.QueueFull: Если очередь переполнена
        """
        if not self._is_running:
            raise RuntimeError("VideoWorker is not running")

        try:
            await self.queue.put(job)
            logger.info(f"Enqueued video cut job: {job.output_file_path}")
        except asyncio.QueueFull:
            logger.error(f"Queue is full, cannot enqueue: {job.output_file_path}")
            raise

    async def _worker(self, worker_id: int) -> None:
        """
        Основной цикл воркера.
        """
        logger.info(f"Worker {worker_id} started")

        while self._is_running:
            try:
                job = await asyncio.wait_for(self.queue.get(), timeout=1.0)

            except asyncio.TimeoutError:
                if self._shutdown_event.is_set():
                    break
                continue

            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break

            try:
                logger.debug(f"Worker {worker_id} processing: {job.output_file_path}")

                result_path = await self.cutter.cut_video_async(
                    input_file_path=job.input_file_path,
                    output_file_path=job.output_file_path,
                    start_time=job.start_time,
                    end_time=job.end_time,
                )

                job.result.set_result(result_path)
                logger.info(f"Worker {worker_id} completed: {job.output_file_path}")

            except Exception as error:
                logger.error(
                    f"Worker {worker_id} failed: {job.output_file_path}", exc_info=True
                )
                job.result.set_exception(error)

            finally:
                self.queue.task_done()

        logger.info(f"Worker {worker_id} stopped")

    async def stop(self, timeout: float = 30.0) -> None:
        """
        Останавливает всех воркеров с graceful shutdown.

        Args:
            timeout: Максимальное время ожидания завершения текущих задач
        """
        if not self._is_running:
            logger.warning("VideoWorker is not running")
            return

        logger.info("Stopping VideoWorker...")
        self._is_running = False
        self._shutdown_event.set()

        if self.tasks:
            try:
                await asyncio.wait_for(self.queue.join(), timeout=timeout)

                for task in self.tasks:
                    if not task.done():
                        task.cancel()

                await asyncio.gather(*self.tasks, return_exceptions=True)

            except asyncio.TimeoutError:
                logger.warning(f"Shutdown timeout ({timeout}s), forcing cancel")
                for task in self.tasks:
                    task.cancel()
                await asyncio.gather(*self.tasks, return_exceptions=True)

        self.tasks.clear()
        logger.info("VideoWorker stopped")

    @property
    def queue_size(self) -> int:
        """Текущий размер очереди"""
        return self.queue.qsize()

    @property
    def is_running(self) -> bool:
        """Статус воркера"""
        return self._is_running
