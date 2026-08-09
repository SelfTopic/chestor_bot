import asyncio
import logging
from pathlib import Path

from ...types.media import VideoCutJob
from .cutter import VideoCutterService

logger = logging.getLogger(__name__)


class VideoWorker:
    def __init__(
        self,
        cutter: VideoCutterService,
        workers_count: int = 2,
    ):
        logger.info("Initializing VideoWorker with %d workers", workers_count)
        self.cutter = cutter
        self.queue: asyncio.Queue[VideoCutJob] = asyncio.Queue()
        self.workers_count = workers_count
        self.tasks = []

    async def start(self):
        logger.info("Starting VideoWorker with %d workers", self.workers_count)
        self.tasks = [
            asyncio.create_task(self._worker()) for _ in range(self.workers_count)
        ]

    async def enqueue(self, job: VideoCutJob):
        logger.info("Enqueuing video cut job: %s", job.output_file_path)
        await self.queue.put(job)

    async def _worker(self):
        while True:
            job = await self.queue.get()

            try:
                result = await self.cutter.cut_video(
                    input_file_path=str(job.input_file_path),
                    output_file_path=str(job.output_file_path),
                    start_time=job.start_time,
                    end_time=job.end_time,
                )

                job.result.set_result(Path(result))
                logger.info(
                    "Finished processing video cut job: %s", job.output_file_path
                )

            except Exception as error:
                logger.error(
                    "Error occurred while processing video cut job: %s",
                    job.output_file_path,
                    exc_info=True,
                )
                job.result.set_exception(error)

            finally:
                self.queue.task_done()

    async def stop(self):
        await self.queue.join()

        for task in self.tasks:
            task.cancel()

        await asyncio.gather(
            *self.tasks,
            return_exceptions=True,
        )

        logger.info("VideoWorker stopped")
