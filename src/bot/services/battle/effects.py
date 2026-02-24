from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw


def _add_arrays(base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
    return np.clip(base.astype(int) + overlay.astype(int), 0, 255).astype(np.uint8)


def render_hit(
    frame: np.ndarray,
    t: float,
    duration: float,
    color: Tuple[int, int, int],
    cx: int,
    cy: int,
    radius: int = 80,
) -> np.ndarray:
    """Вспышка цвета кагунэ — обычный удар."""
    progress = t / duration
    intensity = max(0.0, 1.0 - progress) * 180
    overlay = np.zeros_like(frame)
    img = Image.fromarray(overlay)
    draw = ImageDraw.Draw(img)
    r = int(radius * (0.5 + progress * 0.5))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, int(intensity)))
    return _add_arrays(frame, np.array(img))


def render_miss(
    frame: np.ndarray,
    t: float,
    duration: float,
    cx: int,
    cy: int,
) -> np.ndarray:
    """Серая вспышка — промах."""
    return render_hit(frame, t, duration, (180, 180, 180), cx, cy, radius=60)


def render_block(
    frame: np.ndarray,
    t: float,
    duration: float,
    color: Tuple[int, int, int],
    cx: int,
    cy: int,
) -> np.ndarray:
    """Угловатая вспышка — блок."""
    progress = t / duration
    intensity = max(0.0, 1.0 - progress) * 150
    overlay = np.zeros_like(frame)
    img = Image.fromarray(overlay)
    draw = ImageDraw.Draw(img)
    size = int(70 * (0.5 + progress * 0.5))
    points = [
        (cx, cy - size),
        (cx + size, cy),
        (cx, cy + size),
        (cx - size, cy),
    ]
    draw.polygon(points, fill=(*color, int(intensity)))
    return _add_arrays(frame, np.array(img))


def render_crit(
    frame: np.ndarray,
    t: float,
    duration: float,
    color: Tuple[int, int, int],
    cx: int,
    cy: int,
) -> np.ndarray:
    """Двойная вспышка — крит."""
    progress = t / duration
    wave1 = max(0.0, 1.0 - progress * 2) * 200
    wave2 = max(0.0, 1.0 - max(0.0, progress - 0.4) * 2) * 160
    overlay = np.zeros_like(frame)
    img = Image.fromarray(overlay)
    draw = ImageDraw.Draw(img)
    if wave1 > 0:
        r = int(100 * progress * 2)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, int(wave1)))
    if wave2 > 0:
        r2 = int(60 * max(0.0, progress - 0.4) * 2)
        draw.ellipse(
            [cx - r2, cy - r2, cx + r2, cy + r2], fill=(255, 255, 255, int(wave2))
        )
    return _add_arrays(frame, np.array(img))


def render_regen(
    frame: np.ndarray,
    t: float,
    duration: float,
    cx: int,
    cy: int,
) -> np.ndarray:
    """Зелёное пульсирующее свечение — регенерация."""
    progress = t / duration
    pulse = abs(np.sin(progress * np.pi * 3))
    intensity = int(pulse * 160)
    overlay = np.zeros_like(frame)
    img = Image.fromarray(overlay)
    draw = ImageDraw.Draw(img)
    r = int(50 + pulse * 40)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(50, 220, 80, intensity))
    return _add_arrays(frame, np.array(img))


def render_turn_arrow(
    frame: np.ndarray,
    t: float,
    duration: float,
    attacker_left: bool,
) -> np.ndarray:
    progress = t / duration
    pulse = abs(np.sin(progress * np.pi * 4))
    intensity = int(150 + pulse * 100)

    overlay = np.zeros_like(frame)
    img = Image.fromarray(overlay)
    draw = ImageDraw.Draw(img)

    y = frame.shape[0] // 2
    size = 40

    if attacker_left:
        # стрелка слева направо →
        points = [
            (frame.shape[1] // 4 + size, y),
            (frame.shape[1] // 4, y - size),
            (frame.shape[1] // 4, y + size),
        ]
    else:
        # стрелка справа налево ←
        x = frame.shape[1] * 3 // 4
        points = [
            (x - size, y),
            (x, y - size),
            (x, y + size),
        ]

    draw.polygon(points, fill=(255, 255, 255, intensity))
    return _add_arrays(frame, np.array(img))
