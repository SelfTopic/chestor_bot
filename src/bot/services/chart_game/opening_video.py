import io
from collections.abc import Iterator
from pathlib import Path

from PIL import Image, ImageDraw

from src.bot.game_configs import CHART_CONFIG

from .chart import FPS, SCALE, VIDEOS, ChartPainter, Viewport, draw_timer, glow, label, layer, paste
from ..arcade_art.encoder import write_video
from ..arcade_art.style import BLUE

OPENING_VIDEO = VIDEOS / "opening.mp4"
START = "x1.00"


# Первый экран автомата: пустой график и полоска первых ставок, как после обвала.
class OpeningFrames:
    def __init__(self, fps: int) -> None:
        self.fps = fps
        painter = ChartPainter()
        self.base = painter.sky(0.0)
        paste(self.base, painter.grid(Viewport.at(0.0)))
        paste(self.base, glow(lambda draw, k: label(draw, k, START, 120, BLUE), 18))
        front = layer()
        label(ImageDraw.Draw(front), SCALE, START, 120, BLUE)
        paste(self.base, front)

    @property
    def count(self) -> int:
        return int((CHART_CONFIG.preparation_seconds + CHART_CONFIG.late_edit_seconds) * self.fps)

    def render(self, index: int) -> Image.Image:
        image = self.base.copy()
        draw_timer(image, index / self.fps)
        return image

    def frames(self) -> Iterator[bytes]:
        for index in range(self.count):
            yield self.render(index).tobytes()


def render_opening_video(path: Path, fps: int = FPS) -> None:
    write_video(path, fps, OpeningFrames(fps).frames(), preset="medium")


def opening_picture() -> bytes:
    buffer = io.BytesIO()
    OpeningFrames(fps=1).render(0).save(buffer, "PNG")
    return buffer.getvalue()
