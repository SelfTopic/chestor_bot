import io

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .chart import HEIGHT, SCALE, WIDTH, paste
from .crash_video import CrashFrames
from ..arcade_art.style import LABEL, RED, WHITE, font

LOCK_Y = 150
SHACKLE, BODY_WIDTH, BODY_HEIGHT, STROKE = 30, 84, 64, 10
KEYHOLE = (40, 20, 70)


def _lock(draw: ImageDraw.ImageDraw) -> None:
    x, y = WIDTH / 2 * SCALE, LOCK_Y * SCALE
    arm, stroke = SHACKLE * SCALE, STROKE * SCALE
    draw.arc([x - arm, y - 70 * SCALE, x + arm, y - 10 * SCALE], 180, 360, fill=WHITE, width=stroke)
    for side in (-1, 1):
        post = x + side * (arm - stroke / 2)
        draw.line([(post, y - 40 * SCALE), (post, y - 10 * SCALE)], fill=WHITE, width=stroke)
    half = BODY_WIDTH / 2 * SCALE
    top = y - 14 * SCALE
    draw.rounded_rectangle(
        [x - half, top, x + half, top + BODY_HEIGHT * SCALE], radius=12 * SCALE, fill=WHITE
    )
    hole = 8 * SCALE
    draw.ellipse([x - hole, y + 4 * SCALE, x + hole, y + 4 * SCALE + 2 * hole], fill=KEYHOLE)


def closed_picture(crash: int, title: str, last: str, hint: str) -> bytes:
    image = CrashFrames(crash, fps=1, labeled=False).still().filter(ImageFilter.GaussianBlur(3))
    image = ImageEnhance.Brightness(image).enhance(0.35)
    overlay = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE))
    draw = ImageDraw.Draw(overlay)
    _lock(draw)
    x = WIDTH / 2 * SCALE
    draw.text((x, 285 * SCALE), title, font=font(56 * SCALE, "Black"), fill=WHITE, anchor="mm")
    draw.text((x, 345 * SCALE), last, font=font(26 * SCALE, "SemiBold"), fill=RED, anchor="mm")
    draw.text((x, 400 * SCALE), hint, font=font(24 * SCALE, "Medium"), fill=LABEL, anchor="mm")
    paste(image, overlay)

    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()
