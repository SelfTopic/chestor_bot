import io

from PIL import Image, ImageDraw

from ..arcade_art.style import BACKGROUND_TOP, RED, WHITE, accent, font, mix

WIDTH, HEIGHT = 960, 84
# Больше в полоску всё равно не влезает.
HISTORY_LENGTH = 12
SCALE = 2
MARGIN, GAP, PADDING = 16, 10, 15
# Старые плашки бледнеют, но не до конца: иначе дальние было бы не прочесть.
FADE_STEP, FADE_FLOOR = 0.07, 0.35


def history_strip(history: list[int]) -> bytes:
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), BACKGROUND_TOP)
    draw = ImageDraw.Draw(image)
    caption = font(19 * SCALE, "SemiBold")
    x = MARGIN * SCALE
    for age, crash in enumerate(history):
        color = RED if crash == 100 else accent(crash / 100)
        color = mix(BACKGROUND_TOP, color, max(FADE_FLOOR, 1 - age * FADE_STEP))
        label = f"x{crash / 100:.2f}"
        width = draw.textlength(label, font=caption) + 2 * PADDING * SCALE
        if x + width > (WIDTH - MARGIN) * SCALE:
            break
        draw.rounded_rectangle(
            [x, 20 * SCALE, x + width, (HEIGHT - 20) * SCALE], radius=10 * SCALE, fill=color
        )
        draw.text((x + width / 2, HEIGHT * SCALE / 2), label, font=caption, fill=WHITE, anchor="mm")
        x += width + GAP * SCALE

    buffer = io.BytesIO()
    image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(buffer, "PNG")
    return buffer.getvalue()

