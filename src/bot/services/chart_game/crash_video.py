import io
import math
from collections.abc import Iterator
from pathlib import Path

from PIL import Image, ImageDraw

from src.bot.game_configs import CHART_CONFIG

from .chart import (
    BOTTOM,
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
from .style import GOLD, LABEL, PURPLE, RED, WHITE, accent, font, mix

CRASH_VIDEOS = VIDEOS / "crash"

FALL_SECONDS = 0.8
SPARKS = 14
BAR_WIDTH, BAR_HEIGHT = 320, 10
BAR_Y = CENTER[1] + 100


def crash_video_path(crash: int) -> Path:
    return CRASH_VIDEOS / f"{crash}.mp4"


def _ease_out(share: float) -> float:
    return 1 - (1 - min(max(share, 0.0), 1.0)) ** 3


class CrashFrames:
    def __init__(self, crash: int, fps: int) -> None:
        self.fps = fps
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
        self._timer(image, clock)
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
        paste(image, glow(lambda draw, k: label(draw, k, text, 120, RED, shake), 18))
        label(draw, SCALE, text, 120, RED, shake)
        paste(image, front)
        return image

    @staticmethod
    def _timer(image: Image.Image, clock: float) -> None:
        remaining = max(CHART_CONFIG.preparation_seconds - clock, 0.0)
        share = remaining / CHART_CONFIG.preparation_seconds
        # Полоска меняется на каждом кадре, а остальной кадр стоит: рисуется только её область.
        width, height = BAR_WIDTH + 70, BAR_HEIGHT + 30
        canvas = Image.new("RGBA", (width * SCALE, height * SCALE))
        draw = ImageDraw.Draw(canvas)
        top = (height - BAR_HEIGHT) / 2 * SCALE
        right, bottom = BAR_WIDTH * SCALE, top + BAR_HEIGHT * SCALE
        radius = BAR_HEIGHT / 2 * SCALE
        draw.rounded_rectangle([0, top, right, bottom], radius=radius, fill=(255, 255, 255, 30))
        if share > 0:
            filled = max(right * share, 2 * radius)
            draw.rounded_rectangle([0, top, filled, bottom], radius=radius, fill=PURPLE)
        draw.text(
            (right + 18 * SCALE, height / 2 * SCALE),
            str(math.ceil(remaining)),
            font=font(20 * SCALE, "SemiBold"),
            fill=WHITE if remaining else LABEL,
            anchor="lm",
        )
        canvas = canvas.resize((width, height), Image.Resampling.LANCZOS)
        image.paste(canvas, (round(CENTER[0] - BAR_WIDTH / 2), round(BAR_Y - height / 2)), canvas)


def render_crash_video(path: Path, crash: int, fps: int = FPS) -> None:
    write_video(path, fps, CrashFrames(crash, fps).frames(), preset="medium")


def crash_picture(crash: int) -> bytes:
    buffer = io.BytesIO()
    CrashFrames(crash, fps=1).still().save(buffer, "PNG")
    return buffer.getvalue()
