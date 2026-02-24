from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_MONO = "/usr/share/fonts/noto/NotoSansMono-Bold.ttf"
FONT_CYR = "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"

W, H = 480, 480
BG_COLOR = (10, 10, 10)

EVENT_LABELS = {
    "hit": ("УДАР", (220, 220, 220)),
    "miss": ("ПРОМАХ", (160, 160, 160)),
    "block": ("БЛОК", (100, 180, 255)),
    "crit": ("КРИТИЧЕСКИЙ", (255, 80, 80)),
    "regen": ("РЕГЕНЕРАЦИЯ", (80, 220, 80)),
}


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _hp_color(ratio: float) -> Tuple[int, int, int]:
    if ratio > 0.5:
        return (60, 200, 60)
    elif ratio > 0.25:
        return (220, 180, 30)
    else:
        return (220, 50, 50)


def draw_hp_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    hp: int,
    max_hp: int,
    name: str,
    color: Tuple[int, int, int],
    flip: bool = False,
) -> None:
    """Рисует HP бар с именем. flip=True для правого игрока."""
    bar_h = 16
    ratio = max(0.0, hp / max_hp)
    filled = int(width * ratio)
    hp_color = _hp_color(ratio)

    font_name = _font(FONT_CYR, 18)
    font_hp = _font(FONT_MONO, 14)

    # Имя
    name_display = name[:12] + "…" if len(name) > 12 else name
    if flip:
        draw.text(
            (x + width, y - 22), name_display, font=font_name, fill=color, anchor="ra"
        )
    else:
        draw.text((x, y - 22), name_display, font=font_name, fill=color)

    # Фон бара
    draw.rectangle([x, y, x + width, y + bar_h], fill=(40, 40, 40))

    # Заливка
    if flip:
        draw.rectangle([x + width - filled, y, x + width, y + bar_h], fill=hp_color)
    else:
        draw.rectangle([x, y, x + filled, y + bar_h], fill=hp_color)

    # Обводка цветом кагунэ
    draw.rectangle([x, y, x + width, y + bar_h], outline=color, width=2)

    # Текст HP
    hp_text = f"{max(0, hp)}/{max_hp}"
    if flip:
        draw.text(
            (x + width, y + bar_h + 4),
            hp_text,
            font=font_hp,
            fill=(200, 200, 200),
            anchor="ra",
        )
    else:
        draw.text((x, y + bar_h + 4), hp_text, font=font_hp, fill=(200, 200, 200))


def draw_damage_number(
    draw: ImageDraw.ImageDraw,
    damage: int,
    event_type: str,
    progress: float,
    cx: int,
    cy: int,
) -> None:
    """Цифра урона — вылетает вверх и гаснет."""
    if event_type == "miss":
        text = "MISS"
        color = (160, 160, 160)
    elif event_type == "regen":
        text = f"+{damage} HP"
        color = (80, 220, 80)
    else:
        prefix = "КРИТ! " if event_type == "crit" else ""
        text = f"{prefix}-{damage}"
        color = (255, 80, 80) if event_type == "crit" else (220, 220, 220)

    size = 28 if event_type == "crit" else 22
    font = _font(FONT_MONO, size)
    alpha = int(max(0.0, 1.0 - progress) * 255)
    offset_y = int(progress * 50)

    # Рисуем с тенью
    shadow_color = (0, 0, 0)
    draw.text(
        (cx + 2, cy - offset_y + 2), text, font=font, fill=shadow_color, anchor="mm"
    )
    draw.text((cx, cy - offset_y), text, font=font, fill=(*color[:3],), anchor="mm")


def draw_event_label(
    draw: ImageDraw.ImageDraw,
    event_type: str,
    progress: float,
) -> None:
    """Крупный лейбл события в центре сверху."""
    label, color = EVENT_LABELS.get(event_type, ("", (255, 255, 255)))
    alpha = max(0.0, 1.0 - progress * 1.5)
    if alpha <= 0:
        return
    font = _font(FONT_MONO, 32)
    draw.text((W // 2, 60), label, font=font, fill=color, anchor="mm")


def make_base_frame(
    attacker_hp: int,
    defender_hp: int,
    attacker_max_hp: int,
    defender_max_hp: int,
    attacker_name: str,
    defender_name: str,
    attacker_color: Tuple[int, int, int],
    defender_color: Tuple[int, int, int],
) -> np.ndarray:
    """Базовый кадр с HP барами без эффектов."""
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    bar_w = 180
    bar_y = 40

    # Левый (атакующий)
    draw_hp_bar(
        draw,
        20,
        bar_y,
        bar_w,
        attacker_hp,
        attacker_max_hp,
        attacker_name,
        attacker_color,
        flip=False,
    )

    # Правый (защищающийся) — перевёрнут
    draw_hp_bar(
        draw,
        W - 20 - bar_w,
        bar_y,
        bar_w,
        defender_hp,
        defender_max_hp,
        defender_name,
        defender_color,
        flip=True,
    )

    # Разделитель
    draw.text(
        (W // 2, bar_y + 8),
        "VS",
        font=_font(FONT_MONO, 20),
        fill=(100, 100, 100),
        anchor="mm",
    )

    return np.array(img)
