import io
import math
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

from src.bot.game_configs import CHART_CONFIG

from .chart import (
    CENTER,
    FPS,
    SCALE,
    VIDEOS,
    ChartPainter,
    Viewport,
    curve_glow,
    draw_curve,
    glow,
    label,
    layer,
    paste,
)
from .encoder import write_video
from .style import PURPLE, WHITE, accent

GROWTH_VIDEO = VIDEOS / "growth.mp4"


def frame_count(fps: int) -> int:
    config = CHART_CONFIG
    return int((config.countdown_seconds + config.growth_seconds + config.late_edit_seconds) * fps)


class GrowthFrames:
    def __init__(self, fps: int) -> None:
        self.fps = fps
        self.painter = ChartPainter()

    def render(self, index: int) -> Image.Image:
        clock = index / self.fps
        seconds = min(clock - CHART_CONFIG.countdown_seconds, CHART_CONFIG.growth_seconds)
        multiplier = CHART_CONFIG.multiplier(seconds)
        view = Viewport.at(seconds)

        image = self.painter.sky(clock)
        paste(image, self.painter.grid(view))
        front = layer()
        if seconds > 0:
            color = accent(multiplier)
            curve = view.curve(seconds)
            self.painter.fill_under(image, curve, color)
            paste(image, glow(lambda draw, k: curve_glow(draw, k, curve, color), 12))
            draw_curve(ImageDraw.Draw(front), curve, color)
            text, size, text_color, glow_color = f"x{multiplier:.2f}", 120, color, color
        else:
            remaining = -seconds
            self._countdown_ring(ImageDraw.Draw(front), remaining)
            text, size, text_color, glow_color = str(math.ceil(remaining)), 150, WHITE, PURPLE

        paste(image, glow(lambda draw, k: label(draw, k, text, size, glow_color), 18))
        label(ImageDraw.Draw(front), SCALE, text, size, text_color)
        paste(image, front)
        return image

    @staticmethod
    def _countdown_ring(draw: ImageDraw.ImageDraw, remaining: float) -> None:
        x, y = CENTER[0] * SCALE, CENTER[1] * SCALE
        r = 120 * SCALE
        sweep = 360 * remaining / CHART_CONFIG.countdown_seconds
        draw.arc([x - r, y - r, x + r, y + r], -90, -90 + sweep, fill=PURPLE, width=8 * SCALE)


def opening_picture() -> bytes:
    buffer = io.BytesIO()
    GrowthFrames(fps=1).render(0).save(buffer, "PNG")
    return buffer.getvalue()


# Кадры рисуют несколько процессов, у каждого свои фон и шрифты: шрифты Pillow не передать pickle.
_frames: GrowthFrames | None = None


def _start_worker(fps: int) -> None:
    global _frames
    _frames = GrowthFrames(fps)


def _render_raw(index: int) -> bytes:
    assert _frames is not None
    return _frames.render(index).tobytes()


def render_growth_video(path: Path, fps: int = FPS, workers: int | None = None) -> None:
    # Одно ядро остаётся серверу: иначе проверки здоровья контейнеров не успевают и копятся.
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    # fork из процесса с потоками (бот, pytest-xdist) может зависнуть в дочернем процессе.
    spawn = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(workers, spawn, _start_worker, (fps,)) as pool:
        write_video(path, fps, pool.map(_render_raw, range(frame_count(fps)), chunksize=8))
