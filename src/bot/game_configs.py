from dataclasses import dataclass
from random import randint
from typing import Optional


@dataclass
class KaguneConfig:
    base_price: int = 100
    exponent: float = 1.7
    linear_multiplier: int = 50


KAGUNE_CONFIG = KaguneConfig()


@dataclass
class SnapConfig:
    min_award: int = 500
    max_award: int = 1500

    @property
    def award(self) -> int:
        return randint(self.min_award, self.max_award)


SNAP_CONFIG = SnapConfig()


@dataclass
class CoffeeConfig:
    min_award: int = 5000
    max_award: int = 9000

    snap_limit = 100

    @property
    def award(self) -> int:
        return randint(self.min_award, self.max_award)


COFFEE_CONFIG = CoffeeConfig()


@dataclass
class QuizConfig:
    min_award: int = 5000
    max_award: int = 10000

    @property
    def award(self) -> int:
        return randint(self.min_award, self.max_award)


QUIZ_CONFIG = QuizConfig()


@dataclass
class LotteryConfig:
    """Конфиг для команды депнуть"""

    min_bet: int = 100
    max_bet: int = 100000
    colors: Optional[list[str]] = None

    # Коэффициенты выигрыша и шансы для каждого цвета
    # formato: {цвет: (коэффициент, шанс_в_процентах)}
    color_multipliers: Optional[dict] = None

    def __post_init__(self):
        if self.colors is None:
            self.colors = ["красный", "синий", "зелёный", "белый", "жёлтый"]

        if self.color_multipliers is None:
            self.color_multipliers = {
                "красный": (1.8, 28),
                "синий": (2.5, 22),
                "зелёный": (3.0, 20),
                "жёлтый": (5.0, 13),
                "белый": (
                    10.0,
                    10,
                ),
            }

    def get_multiplier(self, color: str) -> float:
        """Получить коэффициент для цвета"""
        return self.color_multipliers.get(color, 2.0)[0]

    def get_chance(self, color: str) -> int:
        """Получить шанс выпадения цвета в процентах"""
        return self.color_multipliers.get(color, 25)[1]


LOTTERY_CONFIG = LotteryConfig()


@dataclass
class StatUpgradeConfig:
    price_multiplier: int = 2
    multipliers: tuple = (1, 5, 10)

    def price(self, cur_stat: int, count: int = 1) -> int:
        base_total = count * 1500
        scaling_total = int(sum((cur_stat + i) ** 1.35 for i in range(count)))
        return base_total + scaling_total


STAT_UPGRADE_CONFIG = StatUpgradeConfig()

STATS = [
    ("Сила", "strength", "💪"),
    ("Ловкость", "dexterity", "🤸‍♂️"),
    ("Скорость", "speed", "🏃"),
    ("Макс. здоровье", "max_health", "❤️"),
    ("Регенерация", "regeneration", "❣️"),
]
