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
