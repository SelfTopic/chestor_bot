import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Ticker(ABC):
    def __init__(self, interval_seconds: float) -> None:
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None

    @abstractmethod
    async def tick(self) -> None: ...

    @property
    def running(self) -> bool:
        return self._task is not None

    async def start(self) -> None:
        name = type(self).__name__
        if self.running:
            logger.warning("%s is already running", name)
            return

        logger.info("Starting %s (interval=%ss)", name, self._interval)
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("%s stopped", type(self).__name__)

    # Упавший тик не останавливает тикер: следующий пройдёт через интервал.
    async def _loop(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                logger.error("%s tick failed", type(self).__name__, exc_info=True)

            await asyncio.sleep(self._interval)
