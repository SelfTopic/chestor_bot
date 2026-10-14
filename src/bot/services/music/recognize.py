import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shazamio import Shazam

from src.bot.exceptions import MusicError

from ..media_tools import run

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Recognized:
    title: str
    artist: str


class Recognizer:
    def __init__(self) -> None:
        self._shazam = Shazam()

    # Видео, кружок или голосовое сначала сводятся к короткому моно-звуку: Shazam нужен
    # только звук, а большое видео целиком декодировалось бы долго.
    async def recognize(self, source: Path, workdir: Path) -> Recognized | None:
        sound = workdir / "sound.ogg"
        await run(
            "ffmpeg", "-v", "error", "-y", "-i", str(source),
            "-vn", "-ac", "1", "-ar", "16000", "-t", "60", str(sound),
        )  # fmt: skip
        try:
            found: Any = await self._shazam.recognize(str(sound))
        except Exception as exc:
            raise MusicError(f"Shazam: {exc}") from exc
        track = found.get("track") if isinstance(found, dict) else None
        if not isinstance(track, dict) or not track.get("title"):
            return None
        return Recognized(title=str(track["title"]), artist=str(track.get("subtitle") or ""))
