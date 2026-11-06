import random
from collections.abc import Iterator
from dataclasses import dataclass
from typing import NamedTuple

from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.types.dep import DepColor

RED, BLUE, GREEN, YELLOW, WHITE = (
    DepColor.RED,
    DepColor.BLUE,
    DepColor.GREEN,
    DepColor.YELLOW,
    DepColor.WHITE,
)

# Под указателем и по три плашки с каждой стороны: столько видно на экране.
VISIBLE = 7
CENTER = VISIBLE // 2

# Положения покоя: лента всегда останавливается на одном из них, поэтому последний кадр одного
# ролика совпадает с первым кадром следующего. По два на цвет, чтобы соседи не повторялись.
POSITIONS: tuple[tuple[DepColor, ...], ...] = (
    (GREEN, BLUE, YELLOW, RED, BLUE, WHITE, RED),
    (BLUE, RED, GREEN, RED, YELLOW, RED, BLUE),
    (RED, YELLOW, RED, BLUE, GREEN, RED, WHITE),
    (WHITE, GREEN, BLUE, BLUE, RED, YELLOW, GREEN),
    (YELLOW, RED, BLUE, GREEN, RED, BLUE, YELLOW),
    (RED, WHITE, RED, GREEN, BLUE, GREEN, RED),
    (BLUE, RED, GREEN, YELLOW, WHITE, RED, BLUE),
    (GREEN, BLUE, RED, YELLOW, RED, GREEN, RED),
    (RED, GREEN, BLUE, WHITE, RED, YELLOW, BLUE),
    (YELLOW, RED, RED, WHITE, GREEN, BLUE, RED),
)

FILLER = (22, 28)
# Роликов на каждую пару положений: иначе частый игрок узнаёт ролик по началу и знает исход.
VARIANTS = 5
# Насколько лента не доезжает до центра плашки или проезжает его, пока магнит не дотянет.
MISS = (0.15, 0.4)


def color_of(position: int) -> DepColor:
    return POSITIONS[position][CENTER]


def positions_of(color: DepColor) -> list[int]:
    return [index for index, cards in enumerate(POSITIONS) if cards[CENTER] is color]


@dataclass(frozen=True)
class Spin:
    start: int
    end: int
    cards: tuple[DepColor, ...]
    # Доля ширины плашки со знаком: минус — недоехала, плюс — проехала.
    miss: float

    @property
    def start_card(self) -> int:
        return CENTER

    @property
    def end_card(self) -> int:
        return len(self.cards) - VISIBLE + CENTER


class Clip(NamedTuple):
    start: int
    end: int
    variant: int


def clips() -> Iterator[Clip]:
    for start in range(len(POSITIONS)):
        for end in range(len(POSITIONS)):
            for variant in range(VARIANTS):
                yield Clip(start, end, variant)


# Путь зависит только от ролика: где бы набор ни рендерился, он выходит тем же.
def spin(clip: Clip) -> Spin:
    start, end, variant = clip
    rng = random.Random(f"spin-{start}-{end}-{variant}")
    colors = list(DepColor)
    weights = [LOTTERY_CONFIG.get_chance(color.value) for color in colors]
    filler = rng.choices(colors, weights, k=rng.randint(*FILLER))
    miss = rng.uniform(*MISS) * rng.choice((-1, 1))
    return Spin(start, end, POSITIONS[start] + tuple(filler) + POSITIONS[end], miss)
