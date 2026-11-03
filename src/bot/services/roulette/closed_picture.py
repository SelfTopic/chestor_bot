import io

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ..arcade.lock import draw_lock
from ..arcade.style import HEIGHT, LABEL, WHITE, WIDTH, font
from .ribbon import SCALE
from .spin_video import rest_frame

LOCK_Y = 170


def closed_picture(position: int, title: str, hint: str) -> bytes:
    image = rest_frame(position).filter(ImageFilter.GaussianBlur(3))
    image = ImageEnhance.Brightness(image).enhance(0.35)
    overlay = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE))
    draw = ImageDraw.Draw(overlay)
    x = WIDTH / 2 * SCALE
    draw_lock(draw, x, LOCK_Y * SCALE, SCALE)
    draw.text((x, 310 * SCALE), title, font=font(56 * SCALE, "Black"), fill=WHITE, anchor="mm")
    draw.text((x, 375 * SCALE), hint, font=font(24 * SCALE, "Medium"), fill=LABEL, anchor="mm")
    overlay = overlay.resize(image.size, Image.Resampling.LANCZOS)
    image.paste(overlay, (0, 0), overlay)

    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()
