import random
from dataclasses import dataclass

from src.bot.exceptions import UnknownLotteryColor
from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.types.dep import DepColor

# Цвет можно назвать на любом языке бота: «депнуть красный» и «bet red» — одна ставка.
COLOR_WORDS = {
    **{color.value: color for color in DepColor},
    "red": DepColor.RED,
    "blue": DepColor.BLUE,
    "green": DepColor.GREEN,
    "white": DepColor.WHITE,
    "yellow": DepColor.YELLOW,
}


@dataclass(frozen=True)
class Choice:
    color: DepColor | None = None
    amount: int | None = None

    @property
    def complete(self) -> bool:
        return self.color is not None and self.amount is not None

    def merged(self, color: DepColor | None, amount: int | None) -> "Choice":
        return Choice(color or self.color, amount or self.amount)


@dataclass(frozen=True)
class Outcome:
    color: DepColor
    winning: DepColor
    bet: int
    # Изменение баланса: при выигрыше — ставка × коэффициент, при проигрыше — минус ставка.
    earned: int
    balance: int

    @property
    def won(self) -> bool:
        return self.color is self.winning


def draw_color(rng: random.Random) -> DepColor:
    colors = list(DepColor)
    weights = [LOTTERY_CONFIG.get_chance(color.value) for color in colors]
    return rng.choices(colors, weights)[0]


def winnings(color: DepColor, bet: int) -> int:
    return int(bet * LOTTERY_CONFIG.get_multiplier(color.value))


# Слово ищется внутри написанного: «красный!» и «красныйй» — тоже красный.
def parse_color(word: str) -> DepColor:
    written = word.lower().strip()
    for name, color in COLOR_WORDS.items():
        if name in written:
            return color
    raise UnknownLotteryColor(written)
