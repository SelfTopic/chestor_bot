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
    award: int = randint(min_award, max_award)


SNAP_CONFIG = SnapConfig()
