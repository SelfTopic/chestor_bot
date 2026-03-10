"""
Wordle — мини-игра внутри бота.

Сервис самодостаточен: хранит сессии in-memory, содержит
всю игровую логику и рендерит PNG-поле через Pillow.

Не требует БД и репозитория — состояние живёт в словаре
{telegram_id: _WordleGame} внутри экземпляра сервиса.
Сервис регистрируется как Singleton в Container.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from src.bot.game_configs import WORDLE_CONFIG
from src.bot.types.wordle import GuessResult, LetterState, _WordleGame

logger = logging.getLogger(__name__)

# Цвета тёмной темы Wordle
_CLR_BG = (18, 18, 19)
_CLR_EMPTY_FILL = (18, 18, 19)
_CLR_EMPTY_BORDER = (58, 58, 60)
_CLR_CORRECT = (83, 141, 78)
_CLR_PRESENT = (181, 159, 59)
_CLR_ABSENT = (58, 58, 60)
_CLR_TEXT = (255, 255, 255)

_STATE_COLOR = {
    LetterState.CORRECT: _CLR_CORRECT,
    LetterState.PRESENT: _CLR_PRESENT,
    LetterState.ABSENT: _CLR_ABSENT,
}


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    path = "src/assets/fonts/Rubik.ttf"
    if path:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    logger.warning("No suitable font found, falling back to PIL default")
    return ImageFont.load_default()


def _render_board(game: _WordleGame, cell_size: int = 62, gap: int = 6) -> bytes:
    """Нарисовать сетку 6×5 и вернуть PNG-байты."""
    pad = 16
    radius = 4
    font = _load_font(int(cell_size * 0.55))

    grid_w = (
        WORDLE_CONFIG.WORD_LENGTH * cell_size + (WORDLE_CONFIG.WORD_LENGTH - 1) * gap
    )
    grid_h = (
        WORDLE_CONFIG.MAX_ATTEMPTS * cell_size + (WORDLE_CONFIG.MAX_ATTEMPTS - 1) * gap
    )

    img = Image.new("RGB", (grid_w + 2 * pad, grid_h + 2 * pad), _CLR_BG)
    draw = ImageDraw.Draw(img)

    for row in range(WORDLE_CONFIG.MAX_ATTEMPTS):
        guess: Optional[GuessResult] = (
            game.guesses[row] if row < len(game.guesses) else None
        )

        for col in range(WORDLE_CONFIG.WORD_LENGTH):
            x = pad + col * (cell_size + gap)
            y = pad + row * (cell_size + gap)
            x2 = x + cell_size - 1
            y2 = y + cell_size - 1
            cx = x + cell_size // 2
            cy = y + cell_size // 2

            if guess is None:
                draw.rounded_rectangle(
                    [(x, y), (x2, y2)],
                    radius=radius,
                    fill=_CLR_EMPTY_FILL,
                    outline=_CLR_EMPTY_BORDER,
                    width=2,
                )
                continue

            color = _STATE_COLOR[guess.states[col]]
            draw.rounded_rectangle([(x, y), (x2, y2)], radius=radius, fill=color)

            letter = guess.word[col]
            bbox = draw.textbbox((0, 0), letter, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((cx - tw // 2, cy - th // 2), letter, font=font, fill=_CLR_TEXT)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
