"""Подставные часы, генератор, экран и рендер для тестов рулетки."""

import asyncio
import random
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.bot.exceptions import RouletteStaleMedia
from src.bot.services.arcade.media import StoredPicture, StoredVideo, VideoFile
from src.bot.services.roulette import RouletteVideos, Screen, Shown
from src.bot.types.dep import DepColor

START = 0


class ScriptedRandom(random.Random):
    def __init__(self) -> None:
        super().__init__(0)
        self.winning = DepColor.RED

    def choices(self, population, weights=None, *, cum_weights=None, k=1):  # type: ignore[override]
        return [self.winning]

    def choice(self, seq):  # type: ignore[override]
        return seq[-1]

    def randrange(self, start, stop=None, step=1):  # type: ignore[override]
        return START


class FakeTime:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleepers: list[tuple[float, asyncio.Future[None]]] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        future = asyncio.get_running_loop().create_future()
        self.sleepers.append((self.now + seconds, future))
        await future

    async def advance(self, seconds: float) -> None:
        # Задачи, созданные только что, должны успеть заснуть до того, как время сдвинется.
        await asyncio.sleep(0.02)
        self.now += seconds
        for entry in [entry for entry in self.sleepers if entry[0] <= self.now]:
            self.sleepers.remove(entry)
            entry[1].set_result(None)
        for _ in range(5):
            await asyncio.sleep(0.02)


class FakeScreen:
    def __init__(self) -> None:
        self.screens: list[Screen] = []
        self.stale_once = False

    async def show(self, screen: Screen) -> Shown:
        self.screens.append(screen)
        if self.stale_once and isinstance(screen.media, (StoredVideo, StoredPicture)):
            self.stale_once = False
            raise RouletteStaleMedia()
        file_id = "uploaded" if isinstance(screen.media, VideoFile) else None
        return Shown(message_id=42, file_id=file_id)

    async def closed_picture(self, chat_id: int, position: int) -> bytes:
        return f"closed:{position}".encode()

    @property
    def last(self) -> Screen:
        return self.screens[-1]


def fake_render(start: int, end: int, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"video")
    return path


def make_videos(session_factory, tmp_path: Path) -> RouletteVideos:
    return RouletteVideos(
        session_factory,
        spin_path=lambda start, end: tmp_path / f"{start}-{end}.mp4",
        render=fake_render,
        picture=lambda position: f"rest:{position}".encode(),
        executor=lambda: ThreadPoolExecutor(1),
        warm=False,
    )


async def eventually(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(5):
        while not condition():
            await asyncio.sleep(0.01)
