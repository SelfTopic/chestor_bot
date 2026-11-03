import math
from functools import cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "src/assets/fonts/Rubik.ttf"
# Экран у всех автоматов один: ролики и картинки сменяют друг друга в одном сообщении.
WIDTH, HEIGHT = 960, 540

Color = tuple[int, int, int]

BACKGROUND_TOP: Color = (14, 10, 34)
BACKGROUND_BOTTOM: Color = (32, 18, 64)
BACKGROUND_GLOW: Color = (60, 30, 120)
BLUE: Color = (98, 132, 255)
PURPLE: Color = (168, 98, 255)
GOLD: Color = (255, 186, 64)
RED: Color = (255, 72, 96)
WHITE: Color = (255, 255, 255)
LABEL: Color = (150, 140, 200)

# Цвет меняется не скачком, а за последние 8% роста (по логарифму) до порога.
BLEND = 0.08


@cache
def font(size: float, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    result = ImageFont.truetype(FONT, max(4, round(size)))
    result.set_variation_by_name(weight)
    return result


def mix(start: Color, end: Color, share: float) -> Color:
    share = min(max(share, 0.0), 1.0)
    red, green, blue = (round(a + (b - a) * share) for a, b in zip(start, end))
    return red, green, blue


def accent(multiplier: float) -> Color:
    level = math.log(multiplier)
    if level < math.log(2):
        return mix(BLUE, PURPLE, (level - math.log(2) + BLEND) / BLEND)
    return mix(PURPLE, GOLD, (level - math.log(10) + BLEND) / BLEND)


def background(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        draw.line([(0, y), (width, y)], fill=mix(BACKGROUND_TOP, BACKGROUND_BOTTOM, y / height))
    glow = Image.new("L", (width, height))
    ImageDraw.Draw(glow).ellipse(
        [width * 0.25, height * 0.05, width * 0.75, height * 0.7], fill=110
    )
    glow = glow.filter(ImageFilter.GaussianBlur(height * 0.22))
    return Image.composite(Image.new("RGB", (width, height), BACKGROUND_GLOW), image, glow)
