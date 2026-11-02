import math
import random
from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from src.bot.game_configs import CHART_CONFIG

from .style import LABEL, WHITE, Color, background, font

WIDTH, HEIGHT = 960, 540
# Линии и текст рисуются вдвое крупнее и уменьшаются: в Pillow у линий нет сглаживания.
SCALE = 2
# Свечение размывается на холсте в четыре раза меньше: на полном размере это дороже всего кадра.
GLOW_SCALE = 0.25
LEFT, RIGHT, TOP, BOTTOM = 70, WIDTH - 40, 40, HEIGHT - 50
CENTER = (WIDTH / 2, HEIGHT * 0.30)
CURVE_POINTS = 160

Point = tuple[float, float]
Paint = Callable[[ImageDraw.ImageDraw, float], None]


@dataclass(frozen=True)
class Star:
    x: float
    y: float
    radius: float
    brightness: int
    phase: float
    speed: float


@dataclass(frozen=True)
class Viewport:
    seconds: float
    multiplier: float

    @classmethod
    def at(cls, seconds: float) -> "Viewport":
        multiplier = CHART_CONFIG.multiplier(seconds)
        return cls(seconds=max(8.0, seconds * 1.12), multiplier=max(2.0, 1 + (multiplier - 1) * 1.6))

    def point(self, seconds: float, scale: float = SCALE) -> Point:
        multiplier = CHART_CONFIG.multiplier(seconds)
        x = LEFT + (RIGHT - LEFT) * seconds / self.seconds
        y = BOTTOM - (BOTTOM - TOP) * (multiplier - 1) / (self.multiplier - 1)
        return x * scale, y * scale

    def curve(self, seconds: float) -> list[Point]:
        return [self.point(seconds * i / CURVE_POINTS) for i in range(CURVE_POINTS + 1)]


def layer() -> Image.Image:
    return Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE))


def paste(image: Image.Image, overlay: Image.Image) -> None:
    if overlay.size != image.size:
        overlay = overlay.resize(image.size, Image.Resampling.LANCZOS)
    image.paste(overlay, (0, 0), overlay)


def glow(paint: Paint, radius: float) -> Image.Image:
    canvas = Image.new("RGBA", (round(WIDTH * GLOW_SCALE), round(HEIGHT * GLOW_SCALE)))
    paint(ImageDraw.Draw(canvas), GLOW_SCALE)
    canvas = canvas.filter(ImageFilter.GaussianBlur(radius * GLOW_SCALE))
    return canvas.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)


def label(
    draw: ImageDraw.ImageDraw, k: float, text: str, size: float, color: Color, shift: float = 0.0
) -> None:
    position = ((CENTER[0] + shift) * k, CENTER[1] * k)
    draw.text(position, text, font=font(size * k, "Black"), fill=color, anchor="mm")


def curve_glow(draw: ImageDraw.ImageDraw, k: float, curve: list[Point], color: Color) -> None:
    points = [(x / SCALE * k, y / SCALE * k) for x, y in curve[::4] + [curve[-1]]]
    draw.line(points, fill=color + (255,), width=max(3, int(22 * k)), joint="curve")
    x, y = points[-1]
    r = 26 * k
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color + (210,))


def draw_curve(draw: ImageDraw.ImageDraw, curve: list[Point], color: Color, tip: Color = WHITE) -> None:
    draw.line(curve, fill=color, width=5 * SCALE, joint="curve")
    x, y = curve[-1]
    r = 9 * SCALE
    draw.ellipse([x - r, y - r, x + r, y + r], fill=tip)


class ChartPainter:
    def __init__(self) -> None:
        self.background = background(WIDTH, HEIGHT)
        self.fill_gradient = Image.linear_gradient("L").resize((WIDTH, HEIGHT)).point(
            lambda value: int(value * 0.35)
        )
        rng = random.Random(7)
        self.stars = [
            Star(
                x=rng.uniform(0, WIDTH),
                y=rng.uniform(0, HEIGHT * 0.8),
                radius=rng.choice([0.6, 0.6, 1, 1.5]),
                brightness=rng.randint(70, 160),
                phase=rng.uniform(0, 2 * math.pi),
                speed=rng.uniform(0.5, 1.5),
            )
            for _ in range(80)
        ]

    def sky(self, clock: float) -> Image.Image:
        image = self.background.copy()
        draw = ImageDraw.Draw(image)
        for star in self.stars:
            twinkle = 0.55 + 0.45 * math.sin(star.phase + clock * star.speed * 2)
            value = int(star.brightness * twinkle)
            r = star.radius
            draw.ellipse(
                [star.x - r, star.y - r, star.x + r, star.y + r],
                fill=(value, max(value - 10, 0), min(value + 40, 255)),
            )
        return image

    @staticmethod
    def grid(view: Viewport) -> Image.Image:
        canvas = layer()
        draw = ImageDraw.Draw(canvas)
        caption = font(15 * SCALE, "Medium")
        step = next(s for s in (0.2, 0.5, 1, 2, 5, 10, 20) if (view.multiplier - 1) / s <= 5)
        value = (math.floor(1 / step + 1e-9) + 1) * step
        while value < view.multiplier:
            y = (BOTTOM - (BOTTOM - TOP) * (value - 1) / (view.multiplier - 1)) * SCALE
            draw.line([(LEFT * SCALE, y), (RIGHT * SCALE, y)], fill=(255, 255, 255, 18), width=SCALE)
            draw.text(((LEFT - 12) * SCALE, y), f"{value:g}x", font=caption, fill=LABEL, anchor="rm")
            value += step
        time_step = next(s for s in (2, 5, 10) if view.seconds / s <= 6)
        for second in range(0, int(view.seconds) + 1, time_step):
            x = (LEFT + (RIGHT - LEFT) * second / view.seconds) * SCALE
            draw.text((x, (BOTTOM + 22) * SCALE), str(second), font=caption, fill=LABEL, anchor="mm")
        draw.line(
            [(LEFT * SCALE, BOTTOM * SCALE), (RIGHT * SCALE, BOTTOM * SCALE)],
            fill=(255, 255, 255, 40),
            width=SCALE,
        )
        return canvas.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    def fill_under(self, image: Image.Image, curve: list[Point], color: Color) -> None:
        outline = [(x / SCALE, y / SCALE) for x, y in curve]
        mask = Image.new("L", (WIDTH, HEIGHT))
        ImageDraw.Draw(mask).polygon(outline + [(outline[-1][0], BOTTOM), (LEFT, BOTTOM)], fill=255)
        tint = Image.new("RGB", (WIDTH, HEIGHT), color)
        image.paste(tint, (0, 0), ImageChops.multiply(mask, self.fill_gradient))
