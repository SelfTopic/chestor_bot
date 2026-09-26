from dataclasses import dataclass, field
from random import randint, uniform
from typing import List, Optional


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
    colors: Optional[list[str]] = None

    color_multipliers: Optional[dict[str, tuple[float, int]]] = None

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
        if not self.color_multipliers:
            raise ValueError()
        multiplier = self.color_multipliers.get(color)
        if not multiplier:
            raise ValueError()
        return multiplier[0]

    def get_chance(self, color: str) -> int:
        if not self.color_multipliers:
            raise ValueError()
        multiplier = self.color_multipliers.get(color)
        if not multiplier:
            raise ValueError()
        return multiplier[1]


LOTTERY_CONFIG = LotteryConfig()


STAT_CAP_MULTIPLIER = {"max_health": 2.5}


def stat_cap_for_level(level: int, stat_key: str = "") -> int:
    return int(level * 100 * STAT_CAP_MULTIPLIER.get(stat_key, 1.0))


@dataclass
class StatUpgradeConfig:
    price_multiplier: int = 2
    multipliers: tuple = (1, 5, 10)
    stat_price_multiplier: dict = field(default_factory=lambda: {"max_health": 0.4})

    def price(self, cur_stat: int, count: int = 1, stat_key: str = "") -> int:
        base_total = count * 1500
        scaling_total = int(sum((cur_stat + i) ** 1.35 for i in range(count)))
        raw = base_total + scaling_total
        return int(raw * self.stat_price_multiplier.get(stat_key, 1.0))


STAT_UPGRADE_CONFIG = StatUpgradeConfig()

STATS = [
    ("Сила", "strength", "💪"),
    ("Ловкость", "dexterity", "🤸‍♂️"),
    ("Скорость", "speed", "🏃"),
    ("Макс. здоровье", "max_health", "❤️"),
    ("Регенерация", "regeneration", "❣️"),
]


@dataclass
class WordleConfig:
    WORD_LENGTH = 5
    MAX_ATTEMPTS = 6
    min_award = 7000
    max_award = 14000

    @property
    def award(self) -> int:
        return randint(self.min_award, self.max_award)


WORDLE_CONFIG = WordleConfig()


@dataclass
class TransferConfig:
    min_amount: int = 1
    max_amount: int = 100_000
    min_sender_account_age_days: int = 3
    max_received_per_day: int = 10


TRANSFER_CONFIG = TransferConfig()


@dataclass
class PassiveStatsConfig:
    hunger_full_decay_hours: float = 168.0
    kakuja_hunger_decay_multiplier: float = 4.0
    health_regen_per_point_per_hour: float = 1.0
    kagune_type_multiplier: float = 1.8
    kakuja_multiplier: float = 3.0


PASSIVE_STATS_CONFIG = PassiveStatsConfig()


@dataclass
class EatHumanConfig:
    min_hunger_restore: int = 15
    max_hunger_restore: int = 30

    ambush_chance_percent: float = 25.0

    @property
    def hunger_restore(self) -> int:
        return randint(self.min_hunger_restore, self.max_hunger_restore)


EAT_HUMAN_CONFIG = EatHumanConfig()


@dataclass
class LevelUpConfig:
    cheston_min_per_level: int = 1000
    cheston_max_per_level: int = 10000
    rc_min_per_level: int = 5
    rc_max_per_level: int = 20

    def cheston_reward(self, new_level: int) -> int:
        return randint(
            self.cheston_min_per_level * new_level,
            self.cheston_max_per_level * new_level,
        )

    def rc_reward(self, new_level: int) -> int:
        return randint(
            self.rc_min_per_level * new_level, self.rc_max_per_level * new_level
        )


LEVEL_UP_CONFIG = LevelUpConfig()


@dataclass
class BattleConfig:
    max_rounds: int = 30

    physical_block_min: float = 45.0
    physical_block_max: float = 75.0

    modest_block_min: float = 10.0
    modest_block_max: float = 20.0

    kagune_gate_base_percent: float = 50.0

    physical_attack_decay_percent: float = 10.0

    damage_variance_min: float = 0.9
    damage_variance_max: float = 1.1

    fast_attack_damage_variance_min: float = 0.5
    fast_attack_damage_variance_max: float = 0.8

    critical_health_percent: float = 20.0
    regen_heal_variance_min: float = 0.9
    regen_heal_variance_max: float = 1.1

    mutual_ko_winner_hp: float = 1.0

    min_health_to_fight: int = 5

    stat_sensitivity_exponent: float = 0.03


BATTLE_CONFIG = BattleConfig()


@dataclass
class MobConfig:
    stat_multiplier_min: float = 0.5
    stat_multiplier_max: float = 2.0

    names: List[str] = field(
        default_factory=lambda: [
            "Одичавший гуль",
            "Голодный гуль-бродяга",
            "Безумный гуль",
            "Гуль-падальщик",
            "Раненый гуль-изгой",
            "Гуль без имени",
        ]
    )

    level_progress_divisor: float = 5.0

    rc_drop_chance: float = 0.15
    rc_drop_min: int = 1
    rc_drop_max: int = 2

    cheston_reward_reference_stat: str = "strength"
    cheston_reward_multiplier_min: float = 0.7
    cheston_reward_multiplier_max: float = 1.1

    def cheston_reward_for_mob_win(self, ghoul_level: int) -> int:
        floor = stat_cap_for_level(ghoul_level - 1, self.cheston_reward_reference_stat)
        ceiling = stat_cap_for_level(ghoul_level, self.cheston_reward_reference_stat)
        reference_stat = (floor + ceiling) // 2
        price = STAT_UPGRADE_CONFIG.price(reference_stat, 1, self.cheston_reward_reference_stat)
        return round(
            price * uniform(self.cheston_reward_multiplier_min, self.cheston_reward_multiplier_max)
        )


MOB_CONFIG = MobConfig()


@dataclass
class DuelConfig:
    invite_timeout_seconds: int = 60

    serious_or_handicap_timeout_seconds: int = 30
    power_ratio_threshold: float = 2.0

    winner_choice_timeout_seconds: int = 60

    max_battles_per_day_total: int = 20
    max_battles_per_day_pair: int = 5

    eat_rc_multiplier_min: float = 0.3
    eat_rc_multiplier_max: float = 0.6

    rob_percent_min: float = 10.0
    rob_percent_max: float = 25.0


DUEL_CONFIG = DuelConfig()
