from dataclasses import dataclass
from random import randint


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
    min_bet: int = 100
    max_bet: int = 100000
    win_multiplier: float = 2.0
    colors: list[str] = ["красный", "синий", "зелёный", "белый", "жёлтый"]


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
