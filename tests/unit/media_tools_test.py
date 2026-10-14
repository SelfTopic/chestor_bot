"""run(): подпроцессы yt-dlp/ffmpeg. Отменённое или зависшее скачивание убивается вместе со
всем, что успело запустить, и не задевает другие скачивания."""

import asyncio
import os
from pathlib import Path

import pytest

from src.bot.exceptions import MediaToolError
from src.bot.services.media_tools import run


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def child_pid(path: Path) -> int:
    for _ in range(100):
        if path.exists() and path.read_text().strip():
            return int(path.read_text())
        await asyncio.sleep(0.02)
    raise AssertionError("дочерний процесс не запустился")


def spawner(path: Path) -> tuple[str, ...]:
    return ("sh", "-c", f"sleep 300 & echo $! > {path}; wait")


async def wait_dead(pid: int) -> bool:
    for _ in range(100):
        if not alive(pid):
            return True
        await asyncio.sleep(0.02)
    return False


async def test_cancelled_download_kills_its_children_but_not_other_downloads(tmp_path):
    cancelled, other = tmp_path / "cancelled", tmp_path / "other"
    task = asyncio.create_task(run(*spawner(cancelled)))
    neighbour = asyncio.create_task(run(*spawner(other)))
    victim, survivor = await child_pid(cancelled), await child_pid(other)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert await wait_dead(victim)
    assert alive(survivor)
    neighbour.cancel()
    with pytest.raises(asyncio.CancelledError):
        await neighbour
    assert await wait_dead(survivor)


async def test_timed_out_download_kills_its_children(tmp_path):
    path = tmp_path / "pid"
    task = asyncio.create_task(run(*spawner(path), timeout=0.5))
    pid = await child_pid(path)

    with pytest.raises(MediaToolError):
        await task

    assert await wait_dead(pid)
