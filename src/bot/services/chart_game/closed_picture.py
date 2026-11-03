import io

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .chart import HEIGHT, SCALE, WIDTH, paste
from .crash_video import CrashFrames
from ..arcade.lock import draw_lock
from ..arcade.style import LABEL, RED, WHITE, font

LOCK_Y = 150


def closed_picture(crash: int, title: str, last: str, hint: str) -> bytes:
    image = CrashFrames(crash, fps=1, labeled=False).still().filter(ImageFilter.GaussianBlur(3))
    image = ImageEnhance.Brightness(image).enhance(0.35)
    overlay = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE))
    draw = ImageDraw.Draw(overlay)
    draw_lock(draw, WIDTH / 2 * SCALE, LOCK_Y * SCALE, SCALE)
    x = WIDTH / 2 * SCALE
    draw.text((x, 285 * SCALE), title, font=font(56 * SCALE, "Black"), fill=WHITE, anchor="mm")
    draw.text((x, 345 * SCALE), last, font=font(26 * SCALE, "SemiBold"), fill=RED, anchor="mm")
    draw.text((x, 400 * SCALE), hint, font=font(24 * SCALE, "Medium"), fill=LABEL, anchor="mm")
    paste(image, overlay)

    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()
