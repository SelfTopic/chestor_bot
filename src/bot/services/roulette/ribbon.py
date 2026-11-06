from collections.abc import Sequence
from functools import cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.types.dep import DepColor

from ..arcade.style import BACKGROUND_TOP, GOLD, HEIGHT, WIDTH, Color, background, font, mix

# Плашки рисуются вдвое крупнее и уменьшаются: в Pillow у фигур нет сглаживания.
SCALE = 2
CARD_WIDTH, CARD_HEIGHT, GAP = 150, 190, 18
PITCH = CARD_WIDTH + GAP
MIDDLE_Y = HEIGHT // 2
GROW = 14
# Сверху и снизу полосы место под увеличенную плашку.
BAND_TOP = MIDDLE_Y - CARD_HEIGHT // 2 - GROW - 4
BAND_HEIGHT = CARD_HEIGHT + 2 * GROW + 8
POINTER = 22

DARK: Color = BACKGROUND_TOP
CARD_COLORS: dict[DepColor, Color] = {
    DepColor.RED: (255, 72, 96),
    DepColor.BLUE: (80, 130, 255),
    DepColor.GREEN: (52, 211, 140),
    DepColor.YELLOW: (255, 196, 56),
    DepColor.WHITE: (236, 236, 250),
}
DARK_TEXT = {DepColor.YELLOW, DepColor.WHITE}


def multiplier_label(color: DepColor) -> str:
    return f"×{LOTTERY_CONFIG.get_multiplier(color.value):g}"


# Размытие в движении: среднее по горизонтальному окну через накопленные суммы. Полоса в режиме
# RGBa (альфа уже умножена), поэтому края плашек не темнеют.
def motion_blur(band: Image.Image, width: int) -> Image.Image:
    if width < 2:
        return band
    pixels = np.asarray(band, dtype=np.float32)
    padded = np.pad(pixels, ((0, 0), (width // 2 + 1, width - width // 2), (0, 0)))
    sums = np.cumsum(padded, axis=1)
    blurred = (sums[:, width:-1] - sums[:, : -width - 1]) / width + 0.5
    return Image.frombytes("RGBa", band.size, blurred.astype(np.uint8).tobytes())


class RibbonPainter:
    def __init__(self) -> None:
        self.sky = background(WIDTH, HEIGHT)
        self.fade = self._fade()
        self.pointers = self._pointers()

    def frame(
        self,
        cards: Sequence[DepColor],
        offset: float,
        blur: float = 0.0,
        lit: float = 0.0,
        lit_card: int | None = None,
    ) -> Image.Image:
        image = self.sky.copy()
        if lit > 0 and lit_card is not None:
            halo = _halo(cards[lit_card])
            image.paste(halo, (0, 0), halo.getchannel("A").point([round(a * lit) for a in range(256)]))
        band = Image.new("RGBA", (WIDTH * SCALE, BAND_HEIGHT * SCALE))
        draw = ImageDraw.Draw(band)
        for index, color in enumerate(cards):
            x = WIDTH / 2 + index * PITCH - offset
            if -CARD_WIDTH < x < WIDTH + CARD_WIDTH:
                share = lit if index == lit_card else -lit
                _card(draw, x, color, share)
        band = band.convert("RGBa").resize((WIDTH, BAND_HEIGHT), Image.Resampling.LANCZOS)
        band = motion_blur(band, round(blur)).convert("RGBA")
        image.paste(band, (0, BAND_TOP), band)
        image = Image.composite(Image.new("RGB", image.size, DARK), image, self.fade)
        # Линия указателя видна, пока лента едет: на горящей плашке она перечёркивала бы число.
        if lit < 1:
            top, bottom = MIDDLE_Y - CARD_HEIGHT // 2 - GROW, MIDDLE_Y + CARD_HEIGHT // 2 + GROW
            ImageDraw.Draw(image).line(
                [(WIDTH / 2, top + 2), (WIDTH / 2, bottom - 2)], fill=mix(GOLD, DARK, lit), width=3
            )
        image.paste(self.pointers, (0, 0), self.pointers)
        return image

    def _fade(self) -> Image.Image:
        row = np.abs(np.arange(WIDTH) + 0.5 - WIDTH / 2) / (WIDTH / 2)
        strength = np.clip((row - 0.45) / 0.55, 0, 1) ** 1.4 * 255
        mask = np.repeat(strength[np.newaxis, :], HEIGHT, axis=0)
        return Image.fromarray(mask.astype(np.uint8))

    def _pointers(self) -> Image.Image:
        overlay = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE))
        draw = ImageDraw.Draw(overlay)
        x = WIDTH / 2 * SCALE
        top = (MIDDLE_Y - CARD_HEIGHT / 2 - GROW) * SCALE
        bottom = (MIDDLE_Y + CARD_HEIGHT / 2 + GROW) * SCALE
        size = POINTER * SCALE
        for edge, side in ((top, -1), (bottom, 1)):
            base = edge + side * 1.4 * size
            draw.polygon([(x - size, base), (x + size, base), (x, edge)], fill=GOLD)
        return overlay.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


# share > 0 — плашка загорается, share < 0 — гаснет рядом с горящей.
def _card(draw: ImageDraw.ImageDraw, x: float, color: DepColor, share: float) -> None:
    lit, dim = max(share, 0.0), max(-share, 0.0)
    fill = mix(CARD_COLORS[color], DARK, 0.6 * dim)
    grow = GROW * lit
    middle = (MIDDLE_Y - BAND_TOP) * SCALE
    half_width, half_height = (CARD_WIDTH / 2 + grow) * SCALE, (CARD_HEIGHT / 2 + grow) * SCALE
    left, right = x * SCALE - half_width, x * SCALE + half_width
    top, bottom = middle - half_height, middle + half_height
    border = 8 * SCALE
    draw.rounded_rectangle([left, top, right, bottom], radius=22 * SCALE, fill=mix(fill, DARK, 0.25))
    draw.rounded_rectangle(
        [left + border, top + border, right - border, bottom - border], radius=16 * SCALE, fill=fill
    )
    shine = mix(fill, (255, 255, 255), 0.22 - 0.14 * dim)
    draw.rounded_rectangle(
        [left + 18 * SCALE, top + 16 * SCALE, right - 18 * SCALE, top + 40 * SCALE],
        radius=12 * SCALE,
        fill=shine,
    )
    text = DARK if color in DARK_TEXT else (255, 255, 255)
    draw.text(
        (x * SCALE, middle + 6 * SCALE),
        multiplier_label(color),
        font=font((46 + grow) * SCALE, "Black"),
        fill=mix(text, DARK, 0.4 * dim),
        anchor="mm",
    )


@cache
def _halo(color: DepColor) -> Image.Image:
    halo = Image.new("RGBA", (WIDTH, HEIGHT))
    x, y, half = WIDTH / 2, MIDDLE_Y, 110
    ImageDraw.Draw(halo).rounded_rectangle(
        [x - half, y - half, x + half, y + half], radius=40, fill=CARD_COLORS[color] + (170,)
    )
    return halo.filter(ImageFilter.GaussianBlur(30))
