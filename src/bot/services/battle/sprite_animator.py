import logging
import math
from typing import Union

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def _rotate_sprite(sprite: Image.Image, angle: float) -> Image.Image:
    """Поворачивает спрайт вокруг нижнего центра (ног), не обрезая."""
    # Expand=True чтобы не обрезать при повороте
    return sprite.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)


def _apply_red_tint(sprite: Image.Image, intensity: float) -> Image.Image:
    """Накладывает красный оверлей поверх спрайта (intensity 0.0–1.0)."""
    tint = Image.new("RGBA", sprite.size, (220, 30, 30, int(intensity * 180)))
    result = sprite.copy()
    # Смешиваем только там где спрайт непрозрачен
    mask = sprite.split()[3]
    result.paste(tint, mask=mask)
    return result


def _apply_blink(sprite: Image.Image, progress: float) -> Image.Image:
    """Мигание — чередует нормальный и белый спрайт."""
    blink_cycle = math.sin(progress * math.pi * 8)
    if blink_cycle > 0.3:
        white = Image.new("RGBA", sprite.size, (255, 255, 255, 180))
        result = sprite.copy()
        mask = sprite.split()[3]
        result.paste(white, mask=mask)
        return result
    return sprite


def paste_sprite_transformed(
    canvas: Image.Image,
    sprite: Union[Image.Image, np.ndarray],
    cx: int,
    ground_y: int,
    offset_x: int = 0,
    offset_y: int = 0,
    angle: float = 0.0,
) -> None:
    """
    Вставляет спрайт на canvas с трансформациями.
    """
    # Конвертируем numpy array в PIL Image если нужно
    if isinstance(sprite, np.ndarray):
        if sprite.shape[-1] == 4:
            sprite = Image.fromarray(sprite, "RGBA")
        else:
            sprite = Image.fromarray(sprite)

    if not isinstance(sprite, Image.Image):
        raise ValueError(f"Expected PIL Image or numpy array, got {type(sprite)}")

    # Применяем поворот если нужно
    if abs(angle) > 0.1:
        sprite = _rotate_sprite(sprite, angle)

    # Получаем размеры после возможного поворота
    sw, sh = sprite.size

    # Вычисляем позицию для вставки
    x = cx - sw // 2 + offset_x
    y = ground_y - sh + offset_y

    # Создаем маску из альфа-канала
    if sprite.mode == "RGBA":
        # Разделяем каналы
        r, g, b, a = sprite.split()

        # Для отладки сохраняем маску
        if a.getextrema()[0] < 255:
            logger.debug(f"Alpha channel range: {a.getextrema()}")

        # Вставляем с маской
        canvas.paste(sprite, (x, y), mask=a)
    else:
        # Если нет альфа-канала, вставляем как есть
        canvas.paste(sprite, (x, y))


# ── Анимации ──────────────────────────────────────────────────────────────────


def animate_idle(
    sprite: Image.Image,
    progress: float,  # 0.0–1.0 от длительности паузы
) -> tuple[Image.Image, int, int, float]:
    """Лёгкое покачивание в покое. Возвращает (sprite, dx, dy, angle)."""
    sway = math.sin(progress * math.pi * 2) * 2.0
    bob = abs(math.sin(progress * math.pi * 2)) * 1.5
    return sprite, 0, int(-bob), sway


def animate_attacker(
    sprite: Image.Image,
    progress: float,
    direction: int,  # +1 если атакует влево→вправо, -1 иначе
) -> tuple[Image.Image, int, int, float]:
    """
    Рывок вперёд и наклон.
    0.0–0.4 — разгон вперёд
    0.4–0.7 — удар (максимальное смещение)
    0.7–1.0 — возврат
    """
    if progress < 0.4:
        t = progress / 0.4
        ease = t * t  # ease-in
        dx = int(direction * 40 * ease)
        angle = -direction * 15 * ease
    elif progress < 0.7:
        t = (progress - 0.4) / 0.3
        dx = int(direction * 40)
        angle = -direction * 15
    else:
        t = (progress - 0.7) / 0.3
        ease = 1 - (1 - t) ** 2  # ease-out
        dx = int(direction * 40 * (1 - ease))
        angle = -direction * 15 * (1 - ease)

    return sprite, dx, 0, angle


def animate_defender_hit(
    sprite: Image.Image,
    progress: float,
    direction: int,  # направление удара (+1 или -1)
) -> tuple[Image.Image, int, int, float]:
    """
    Красный тинт + встряска + отброс + мигание при получении урона.
    0.0–0.2 — мгновенный отброс + яркий tint
    0.2–0.6 — встряска + угасающий tint
    0.6–1.0 — возврат на место + мигание
    """
    if progress < 0.2:
        t = progress / 0.2
        knockback = int(direction * 25 * t)
        tint_intensity = 0.8
        shake_x = 0
        blink = False
    elif progress < 0.6:
        t = (progress - 0.2) / 0.4
        knockback = int(direction * 25 * (1 - t * 0.6))
        tint_intensity = 0.8 * (1 - t)
        shake_x = int(math.sin(t * math.pi * 6) * 8)
        blink = False
    else:
        t = (progress - 0.6) / 0.4
        knockback = int(direction * 10 * (1 - t))
        tint_intensity = 0.0
        shake_x = 0
        blink = True

    result = sprite
    if tint_intensity > 0:
        result = _apply_red_tint(result, tint_intensity)
    if blink and progress < 0.9:
        result = _apply_blink(result, progress)

    return result, knockback + shake_x, 0, 0.0


def animate_defender_block(
    sprite: Image.Image,
    progress: float,
    direction: int,
) -> tuple[Image.Image, int, int, float]:
    """Небольшой отброс без тинта — блок поглотил удар."""
    if progress < 0.3:
        t = progress / 0.3
        dx = int(direction * 10 * t)
    else:
        t = (progress - 0.3) / 0.7
        dx = int(direction * 10 * (1 - t))

    return sprite, dx, 0, 0.0


def animate_regen(
    sprite: Image.Image,
    progress: float,
) -> tuple[Image.Image, int, int, float]:
    """Зелёный пульс поверх спрайта."""
    pulse = abs(math.sin(progress * math.pi * 3))
    tint = Image.new("RGBA", sprite.size, (30, 220, 80, int(pulse * 160)))
    result = sprite.copy()
    mask = sprite.split()[3]
    result.paste(tint, mask=mask)
    bob = int(math.sin(progress * math.pi * 3) * 4)
    return result, 0, -bob, 0.0


def animate_miss(
    sprite: Image.Image,
    progress: float,
    direction: int,
) -> tuple[Image.Image, int, int, float]:
    """Лёгкий замах который ни во что не попал."""
    if progress < 0.5:
        t = progress / 0.5
        dx = int(direction * 20 * math.sin(t * math.pi))
        angle = -direction * 8 * math.sin(t * math.pi)
    else:
        dx, angle = 0, 0.0
    return sprite, dx, 0, angle
