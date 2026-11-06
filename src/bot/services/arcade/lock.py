from PIL import ImageDraw

from .style import WHITE

SHACKLE, BODY_WIDTH, BODY_HEIGHT, STROKE = 30, 84, 64, 10
KEYHOLE = (40, 20, 70)


# Замок закрытого автомата; x, y — центр, scale — во сколько раз холст крупнее экрана.
def draw_lock(draw: ImageDraw.ImageDraw, x: float, y: float, scale: float) -> None:
    arm, stroke = SHACKLE * scale, round(STROKE * scale)
    draw.arc([x - arm, y - 70 * scale, x + arm, y - 10 * scale], 180, 360, fill=WHITE, width=stroke)
    for side in (-1, 1):
        post = x + side * (arm - stroke / 2)
        draw.line([(post, y - 40 * scale), (post, y - 10 * scale)], fill=WHITE, width=stroke)
    half = BODY_WIDTH / 2 * scale
    top = y - 14 * scale
    draw.rounded_rectangle(
        [x - half, top, x + half, top + BODY_HEIGHT * scale], radius=12 * scale, fill=WHITE
    )
    hole = 8 * scale
    draw.ellipse([x - hole, y + 4 * scale, x + hole, y + 4 * scale + 2 * hole], fill=KEYHOLE)
