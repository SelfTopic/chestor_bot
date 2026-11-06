import asyncio
import tarfile
from pathlib import Path

import aiohttp

from .spin_video import VIDEO_SET, VIDEOS

RELEASE = f"roulette-videos-{VIDEO_SET}"
ARCHIVE = f"{RELEASE}.tar"
# Распаковку могут прервать на середине, поэтому полноту набора отмечает отдельный файл.
COMPLETE = ".complete"
DOWNLOAD_TIMEOUT_SECONDS = 1800


def release_url(repo: str) -> str:
    return f"https://github.com/{repo}/releases/download/{RELEASE}/{ARCHIVE}"


class VideoSet:
    def __init__(self, url: str, folder: Path = VIDEOS) -> None:
        self._url = url
        self._folder = folder

    @property
    def complete(self) -> bool:
        return (self._folder / COMPLETE).exists()

    async def download(self) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        archive = self._folder.parent / f".{ARCHIVE}.partial"
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_SECONDS)
        try:
            async with (
                aiohttp.ClientSession(timeout=timeout) as http,
                http.get(self._url) as response,
            ):
                response.raise_for_status()
                with archive.open("wb") as file:
                    async for chunk in response.content.iter_chunked(1 << 20):
                        file.write(chunk)
            await asyncio.to_thread(self._unpack, archive)
        finally:
            archive.unlink(missing_ok=True)

    def _unpack(self, archive: Path) -> None:
        with tarfile.open(archive) as tar:
            tar.extractall(self._folder, filter="data")
        (self._folder / COMPLETE).touch()


def pack(folder: Path, archive: Path) -> None:
    with tarfile.open(archive, "w") as tar:
        for video in sorted(folder.glob("*.mp4")):
            tar.add(video, arcname=video.name)
