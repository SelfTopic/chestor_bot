import io
import math
from collections.abc import Iterator
from pathlib import Path

from PIL import Image, ImageDraw

from src.bot.game_configs import CHART_CONFIG

from .chart import (
    BOTTOM,
    FPS,
    SCALE,
    VIDEOS,
    ChartPainter,
    Viewport,
    curve_glow,
    draw_curve,
    draw_timer,
    glow,
    label,
    layer,
    paste,
)
from ..arcade_art.encoder import write_video
from ..arcade_art.style import GOLD, RED, accent, mix

CRASH_VIDEOS = VIDEOS / "crash"

FALL_SECONDS = 0.8
SPARKS = 14


def crash_video_path(crash: int) -> Path:
    return CRASH_VIDEOS / f"{crash}.mp4"


def _ease_out(share: float) -> float:
    return 1 - (1 - min(max(share, 0.0), 1.0)) ** 3


class CrashFrames:
    def __init__(self, crash: int, fps: int, labeled: bool = True) -> None:
        self.fps = fps
        self.labeled = labeled
        self.multiplier = multiplier = crash / 100
        self.painter = ChartPainter()
        seconds = CHART_CONFIG.seconds_to(multiplier)
        self.view = Viewport.at(seconds)
        self.curve = self.view.curve(seconds) if seconds > 0 else [self.view.point(0)] * 2
        self.grid = self.painter.grid(self.view)
        self.frozen: Image.Image | None = None

    @property
    def count(self) -> int:
        return int((CHART_CONFIG.preparation_seconds + CHART_CONFIG.late_edit_seconds) * self.fps)

    def frames(self) -> Iterator[bytes]:
        for index in range(self.count):
            yield self.render(index).tobytes()

    def still(self) -> Image.Image:
        return self._falling(1.0)

    def render(self, index: int) -> Image.Image:
        clock = index / self.fps
        if clock < FALL_SECONDS:
            image = self._falling(clock / FALL_SECONDS)
        else:
            if self.frozen is None:
                self.frozen = self._falling(1.0)
            image = self.frozen.copy()
        draw_timer(image, clock)
        return image

    def _falling(self, share: float) -> Image.Image:
        fall = _ease_out(share)
        color = mix(accent(self.multiplier), RED, share / 0.2)
        image = self.painter.sky(0.0)
        paste(image, self.grid)
        curve = self.curve
        self.painter.fill_under(image, curve, color)

        tip_x, tip_y = curve[-1]
        drop = (tip_x + 30 * SCALE * fall, tip_y + (BOTTOM * SCALE - tip_y) * fall)
        falling = curve + [drop]
        paste(image, glow(lambda draw, k: curve_glow(draw, k, falling, RED), 12))

        flash = Image.new("RGBA", image.size, RED + (int(80 * (1 - share) ** 2),))
        paste(image, flash)

        front = layer()
        draw = ImageDraw.Draw(front)
        draw_curve(draw, curve, color, tip=color)
        draw.line([curve[-1], drop], fill=RED, width=5 * SCALE)
        r = 9 * SCALE
        draw.ellipse([drop[0] - r, drop[1] - r, drop[0] + r, drop[1] + r], fill=RED)
        for spark in range(SPARKS):
            angle = 2 * math.pi * spark / SPARKS + 0.3
            distance = 80 * SCALE * fall
            size = 5 * SCALE * (1 - share)
            x = tip_x + math.cos(angle) * distance
            y = tip_y + math.sin(angle) * distance
            if size > 0:
                draw.ellipse([x - size, y - size, x + size, y + size], fill=GOLD if spark % 2 else RED)

        shake = math.sin(share * 40) * 10 * (1 - share) ** 2
        text = f"x{self.multiplier:.2f}"
        if self.labeled:
            paste(image, glow(lambda draw, k: label(draw, k, text, 120, RED, shake), 18))
            label(draw, SCALE, text, 120, RED, shake)
        paste(image, front)
        return image


def render_crash_video(path: Path, crash: int, fps: int = FPS) -> None:
    write_video(path, fps, CrashFrames(crash, fps).frames(), preset="medium")


# Без числа: общая картинка обвала, пока ролика с нужным числом нет; число — в тексте.
UNLABELED_CRASH = 300


def crash_picture(crash: int, labeled: bool = True) -> bytes:
    buffer = io.BytesIO()
    CrashFrames(crash, fps=1, labeled=labeled).still().save(buffer, "PNG")
    return buffer.getvalue()
