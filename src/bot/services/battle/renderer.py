from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.bot.services.battle.sprite_animator import paste_sprite_transformed

FONT_MONO = "/usr/share/fonts/noto/NotoSansMono-Bold.ttf"
FONT_CYR = "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"

W, H = 360, 360
BG_COLOR = (10, 10, 10)


BAR_W = int(W * 0.38)  # ширина HP бара  (~137px при 360)
BAR_X = int(W * 0.05)  # отступ от края  (~18px)
BAR_Y = int(H * 0.10)  # y-позиция HP бара (~36px)
BAR_H = int(H * 0.044)  # высота прямоугольника бара (~16px)
GROUND_Y = int(H * 0.83)  # "пол" для ног спрайта
DMG_Y = int(H * 0.25)  # высота цифры урона
LABEL_Y = int(H * 0.16)  # высота event label
ARROW_Y = int(H * 0.65)  # высота стрелки между бойцами
LOG_Y = int(H * 0.87)  # строка лога внизу
LEFT_CX = W // 4  # центр левого бойца
RIGHT_CX = W * 3 // 4  # центр правого бойца

EVENT_LABELS = {
    "hit": ("УДАР", (220, 220, 220)),
    "miss": ("ПРОМАХ", (160, 160, 160)),
    "block": ("БЛОК", (100, 180, 255)),
    "crit": ("КРИТИЧЕСКИЙ", (255, 80, 80)),
    "regen": ("РЕГЕНЕРАЦИЯ", (80, 220, 80)),
}

# ==========================================================
# Шрифты — загружаются один раз при импорте модуля
# ==========================================================
_FONT_CACHE: dict = {}


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(path, size)
    return _FONT_CACHE[key]


def _preload_fonts() -> None:
    sizes_mono = [12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 48]
    sizes_cyr = [14, 16, 18, 20, 24, 28, 36, 42]
    for s in sizes_mono:
        _font(FONT_MONO, s)
    for s in sizes_cyr:
        _font(FONT_CYR, s)


_preload_fonts()


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
    bar_h = BAR_H
    ratio = max(0.0, hp / max_hp)
    filled = int(width * ratio)
    hp_color = _hp_color(ratio)

    font_name = _font(FONT_CYR, 14)
    font_hp = _font(FONT_MONO, 12)

    name_display = name[:12] + "…" if len(name) > 12 else name
    name_offset = int(H * 0.055)  # ~20px при 360

    if flip:
        draw.text(
            (x + width, y - name_offset),
            name_display,
            font=font_name,
            fill=color,
            anchor="ra",
        )
    else:
        draw.text((x, y - name_offset), name_display, font=font_name, fill=color)

    draw.rectangle([x, y, x + width, y + bar_h], fill=(40, 40, 40))

    if flip:
        draw.rectangle([x + width - filled, y, x + width, y + bar_h], fill=hp_color)
    else:
        draw.rectangle([x, y, x + filled, y + bar_h], fill=hp_color)

    draw.rectangle([x, y, x + width, y + bar_h], outline=color, width=2)

    hp_text = f"{max(0, hp)}/{max_hp}"
    if flip:
        draw.text(
            (x + width, y + bar_h + 3),
            hp_text,
            font=font_hp,
            fill=(200, 200, 200),
            anchor="ra",
        )
    else:
        draw.text((x, y + bar_h + 3), hp_text, font=font_hp, fill=(200, 200, 200))


def draw_damage_number(
    draw: ImageDraw.ImageDraw,
    damage: int,
    event_type: str,
    progress: float,
    cx: int,
    cy: int,
) -> None:
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

    size = int(H * 0.072) if event_type == "crit" else int(H * 0.056)
    font = _font(FONT_MONO, size)
    offset_y = int(progress * H * 0.13)

    draw.text((cx + 2, cy - offset_y + 2), text, font=font, fill=(0, 0, 0), anchor="mm")
    draw.text((cx, cy - offset_y), text, font=font, fill=color, anchor="mm")


def draw_event_label(
    draw: ImageDraw.ImageDraw,
    event_type: str,
    progress: float,
) -> None:
    label, color = EVENT_LABELS.get(event_type, ("", (255, 255, 255)))
    if max(0.0, 1.0 - progress * 1.5) <= 0:
        return
    font = _font(FONT_MONO, int(H * 0.067))  # ~24px при 360
    draw.text((W // 2, LABEL_Y), label, font=font, fill=color, anchor="mm")


def paste_sprite(
    img: Image.Image,
    sprite: Image.Image,
    cx: int,
    ground_y: int = None,
) -> None:
    if ground_y is None:
        ground_y = GROUND_Y
    sw, sh = sprite.size
    x = cx - sw // 2
    y = ground_y - sh
    img.paste(sprite, (x, y), mask=sprite.split()[3])


def make_base_frame(
    left_hp: int,
    right_hp: int,
    left_max_hp: int,
    right_max_hp: int,
    left_name: str,
    right_name: str,
    left_color: tuple,
    right_color: tuple,
    left_sprite=None,
    right_sprite=None,
    left_sprite_offset: tuple[int, int] = (0, 0),
    right_sprite_offset: tuple[int, int] = (0, 0),
    left_sprite_angle: float = 0.0,
    right_sprite_angle: float = 0.0,
    attacker_left: Optional[bool] = None,  # None = idle/pause
) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    def _paste_left():
        if left_sprite is not None:
            paste_sprite_transformed(
                img,
                left_sprite,
                cx=LEFT_CX,
                ground_y=GROUND_Y,
                offset_x=left_sprite_offset[0],
                offset_y=left_sprite_offset[1],
                angle=left_sprite_angle,
            )

    def _paste_right():
        if right_sprite is not None:
            paste_sprite_transformed(
                img,
                right_sprite,
                cx=RIGHT_CX,
                ground_y=GROUND_Y,
                offset_x=right_sprite_offset[0],
                offset_y=right_sprite_offset[1],
                angle=right_sprite_angle,
            )

    # Атакующий рисуется последним — он поверх защитника
    if attacker_left is True:
        _paste_left()
        _paste_right()
    else:
        # attacker_left=False или None (idle) — правый поверх левого
        _paste_right()
        _paste_left()

    # HP бары всегда поверх спрайтов
    draw_hp_bar(
        draw,
        BAR_X,
        BAR_Y,
        BAR_W,
        left_hp,
        left_max_hp,
        left_name,
        left_color,
        flip=False,
    )
    draw_hp_bar(
        draw,
        W - BAR_X - BAR_W,
        BAR_Y,
        BAR_W,
        right_hp,
        right_max_hp,
        right_name,
        right_color,
        flip=True,
    )
    draw.text(
        (W // 2, BAR_Y + BAR_H // 2),
        "VS",
        font=_font(FONT_MONO, int(H * 0.044)),
        fill=(100, 100, 100),
        anchor="mm",
    )

    return np.array(img)


ACTION_ICONS = {
    "hit": "",
    "miss": "",
    "block": "",
    "crit": "",
    "regen": "",
}


def draw_action_overlay(
    draw: ImageDraw.ImageDraw,
    event_type: str,
    attacker_name: str,
    defender_name: str,
    attacker_color: Tuple[int, int, int],
    defender_color: Tuple[int, int, int],
    attacker_left: bool,
    progress: float,
) -> None:
    font_name = _font(FONT_CYR, int(H * 0.044))  # ~16px
    font_icon = _font(FONT_MONO, int(H * 0.05))  # ~18px

    alpha_scale = max(0.0, 1.0 - progress * 1.2)
    fade = lambda c: tuple(int(v * alpha_scale) for v in c)

    icon = ACTION_ICONS.get(event_type, "?")

    if attacker_left:
        atk_x, atk_anchor = BAR_X, "la"
        def_x, def_anchor = W - BAR_X, "ra"
    else:
        atk_x, atk_anchor = W - BAR_X, "ra"
        def_x, def_anchor = BAR_X, "la"

    draw.text(
        (atk_x, LOG_Y),
        attacker_name,
        font=font_name,
        fill=fade(attacker_color),
        anchor=atk_anchor,
    )
    draw.text(
        (def_x, LOG_Y),
        defender_name,
        font=font_name,
        fill=fade(defender_color),
        anchor=def_anchor,
    )
    draw.text(
        (W // 2, LOG_Y),
        f" {icon} ",
        font=font_icon,
        fill=fade((220, 220, 220)),
        anchor="ma",
    )

    arrow_dx = int(W * 0.08)
    tip_x = W // 2 + (arrow_dx if attacker_left else -arrow_dx)
    tail_x = W // 2 - (arrow_dx if attacker_left else -arrow_dx)
    fade_gray = fade((200, 200, 200))

    draw.line([(tail_x, ARROW_Y), (tip_x, ARROW_Y)], fill=fade_gray, width=2)

    tip_size = int(W * 0.022)  # ~8px
    if attacker_left:
        draw.polygon(
            [
                (tip_x, ARROW_Y),
                (tip_x - tip_size, ARROW_Y - tip_size // 2),
                (tip_x - tip_size, ARROW_Y + tip_size // 2),
            ],
            fill=fade_gray,
        )
    else:
        draw.polygon(
            [
                (tip_x, ARROW_Y),
                (tip_x + tip_size, ARROW_Y - tip_size // 2),
                (tip_x + tip_size, ARROW_Y + tip_size // 2),
            ],
            fill=fade_gray,
        )
