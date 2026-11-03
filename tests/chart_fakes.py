"""Подставные часы, генератор и рендер для тестов игры «График»."""

import asyncio
import random
from pathlib import Path

from src.bot.services.chart_game import ChartGameService


class FixedRandom(random.Random):
    def __init__(self, value: float) -> None:
        super().__init__()
        self.value = value

    def random(self) -> float:
        return self.value


class FakeTime:
    def __init__(self) -> None:
        self.now = 1000.0
        self._sleepers: list[tuple[float, asyncio.Future[None]]] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        future = asyncio.get_running_loop().create_future()
        self._sleepers.append((self.now + seconds, future))
        await future

    async def advance_to(self, moment: float, service: ChartGameService) -> None:
        self.now = moment
        woken = [(d, f) for d, f in self._sleepers if d <= moment]
        for entry in woken:
            self._sleepers.remove(entry)
            entry[1].set_result(None)
        await self.until_blocked(service)

    async def until_blocked(self, service: ChartGameService) -> None:
        async with asyncio.timeout(10):
            while len(self._sleepers) < len(service._tasks):
                await asyncio.sleep(0.01)


def fake_render(path: Path, crash: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"video")
