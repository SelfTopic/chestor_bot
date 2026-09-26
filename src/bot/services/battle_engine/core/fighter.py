from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ....game_configs import BATTLE_CONFIG, PASSIVE_STATS_CONFIG
from ....types import KaguneType
from ....utils.regen_calculate import get_hunger_tier
from .actions import RoundActionType
from .errors import InvalidBattleStatsError
from .formulas import compress_stat_advantage, regen_proc_chance


KAGUNE_TYPE_MULTIPLIERS: Dict[KaguneType, Dict[str, float]] = {
    KaguneType.UKAKU: {"speed": 1.8},
    KaguneType.KOUKAKU: {"strength": 1.6, "speed": 1.3},
    KaguneType.RINKAKU: {
        "dexterity": 1.3,
        "regeneration": 1.8,
        "speed": 1.5,
        "health": 1.5,
    },
    KaguneType.BIKAKU: {
        "strength": 1.5,
        "dexterity": 1.4,
        "regeneration": 1.4,
        "speed": 1.4,
        "health": 1.4,
    },
}

KAGUNE_TYPE_PRIORITY_STAT: Dict[KaguneType, str] = {
    KaguneType.UKAKU: "speed",
    KaguneType.KOUKAKU: "strength",
    KaguneType.RINKAKU: "regeneration",
    KaguneType.BIKAKU: "health",
}


def resolve_kagune_multiplier(stat: str, owned_types: List[KaguneType]) -> float:
    touching = [t for t in owned_types if stat in KAGUNE_TYPE_MULTIPLIERS.get(t, {})]
    if not touching:
        return 1.0

    owner = next((t for t in touching if KAGUNE_TYPE_PRIORITY_STAT[t] == stat), None)
    if owner is not None:
        return KAGUNE_TYPE_MULTIPLIERS[owner][stat]

    return min(KAGUNE_TYPE_MULTIPLIERS[t][stat] for t in touching)


@dataclass(frozen=True)
class FighterSnapshot:
    id: int
    name: str
    strength: int
    dexterity: int
    regeneration: int
    speed: int
    health: int
    hunger: int
    is_kakuja: bool
    kagune_strength: Dict[KaguneType, int] = field(default_factory=dict)
    max_health: Optional[int] = None

    def __post_init__(self) -> None:
        if self.max_health is None:
            object.__setattr__(self, "max_health", self.health)

    @property
    def owned_kagune_types(self) -> List[KaguneType]:
        return list(self.kagune_strength.keys())

    @property
    def total_kagune_strength(self) -> int:
        return sum(self.kagune_strength.values())


@dataclass(frozen=True)
class EffectiveStats:
    strength: float
    dexterity: float
    regeneration: float
    speed: float
    health: float
    kagune_strength: float


def validate_snapshot(fighter: FighterSnapshot) -> None:
    if fighter.dexterity <= 0 or fighter.speed <= 0:
        raise InvalidBattleStatsError(
            f"Fighter {fighter.id} ({fighter.name}): dexterity/speed must be > 0, "
            f"got dexterity={fighter.dexterity}, speed={fighter.speed}"
        )
    if fighter.strength < 0 or fighter.regeneration < 0 or fighter.health <= 0:
        raise InvalidBattleStatsError(
            f"Fighter {fighter.id} ({fighter.name}): strength/regeneration must be "
            f">= 0 and health > 0, got strength={fighter.strength}, "
            f"regeneration={fighter.regeneration}, health={fighter.health}"
        )
    if not 0 <= fighter.hunger <= 100:
        raise InvalidBattleStatsError(
            f"Fighter {fighter.id} ({fighter.name}): hunger must be in [0, 100], "
            f"got hunger={fighter.hunger}"
        )
    if any(value < 0 for value in fighter.kagune_strength.values()):
        raise InvalidBattleStatsError(
            f"Fighter {fighter.id} ({fighter.name}): kagune_strength values must "
            f"be >= 0, got {fighter.kagune_strength}"
        )


@dataclass(frozen=True)
class StatBreakdown:
    base: float
    after_hunger: float
    after_kagune: float


def compute_stat_breakdown(fighter: FighterSnapshot) -> Dict[str, StatBreakdown]:
    tier = get_hunger_tier(fighter.hunger)
    owned = fighter.owned_kagune_types
    kakuja_mult = PASSIVE_STATS_CONFIG.kakuja_multiplier if fighter.is_kakuja else 1.0

    def breakdown(base: float, stat_name: str, is_rising: bool) -> StatBreakdown:
        hunger_mult = tier.rising_multiplier if is_rising else tier.falling_multiplier
        after_hunger = base * hunger_mult
        kagune_mult = resolve_kagune_multiplier(stat_name, owned)
        after_kagune = after_hunger * kagune_mult * kakuja_mult
        return StatBreakdown(base=base, after_hunger=after_hunger, after_kagune=after_kagune)

    return {
        "strength": breakdown(fighter.strength, "strength", is_rising=True),
        "dexterity": breakdown(fighter.dexterity, "dexterity", is_rising=False),
        "speed": breakdown(fighter.speed, "speed", is_rising=False),
        "health": breakdown(fighter.health, "health", is_rising=False),
        "regeneration": breakdown(fighter.regeneration, "regeneration", is_rising=False),
    }


def compute_effective_stats(fighter: FighterSnapshot) -> EffectiveStats:
    breakdown = compute_stat_breakdown(fighter)
    tier = get_hunger_tier(fighter.hunger)
    kakuja_mult = PASSIVE_STATS_CONFIG.kakuja_multiplier if fighter.is_kakuja else 1.0

    kagune_strength = fighter.total_kagune_strength * tier.rising_multiplier * kakuja_mult

    return EffectiveStats(
        strength=breakdown["strength"].after_kagune,
        dexterity=breakdown["dexterity"].after_kagune,
        regeneration=breakdown["regeneration"].after_kagune,
        speed=breakdown["speed"].after_kagune,
        health=breakdown["health"].after_kagune,
        kagune_strength=kagune_strength,
    )


class Fighter:
    def __init__(self, snapshot: FighterSnapshot) -> None:
        validate_snapshot(snapshot)

        self.snapshot = snapshot
        self.stats: EffectiveStats = compute_effective_stats(snapshot)
        self.current_hp: float = self.stats.health
        self.physical_streak: int = 0
        self.regen_guaranteed_used: bool = False
        self.regen_roll_used: bool = False

    @property
    def id(self) -> int:
        return self.snapshot.id

    @property
    def name(self) -> str:
        return self.snapshot.name

    @property
    def is_defeated(self) -> bool:
        return self.current_hp <= 0

    def take_damage(self, amount: float) -> None:
        self.current_hp = max(0.0, self.current_hp - amount)

    def is_critical(self) -> bool:
        if self.current_hp <= 0:
            return False
        threshold = self.stats.health * (BATTLE_CONFIG.critical_health_percent / 100.0)
        return self.current_hp < threshold

    def decide_action(self, opponent: "Fighter", rng: random.Random) -> RoundActionType:
        if not self.is_critical():
            return RoundActionType.ATTACK

        if not self.regen_guaranteed_used:
            self.regen_guaranteed_used = True
            return RoundActionType.REGEN

        if not self.regen_roll_used:
            self.regen_roll_used = True
            chance = regen_proc_chance(self.stats.regeneration, opponent.stats.regeneration)
            if rng.random() * 100.0 < chance:
                return RoundActionType.REGEN

        return RoundActionType.ATTACK

    def apply_heal(self, opponent: "Fighter", rng: random.Random) -> float:
        variance = rng.uniform(
            BATTLE_CONFIG.regen_heal_variance_min, BATTLE_CONFIG.regen_heal_variance_max
        )
        effective_regeneration = compress_stat_advantage(
            self.stats.regeneration, opponent.stats.regeneration
        )
        heal = variance * effective_regeneration
        new_hp = min(self.stats.health, self.current_hp + heal)
        healed = new_hp - self.current_hp
        self.current_hp = new_hp
        return healed


__all__ = [
    "KAGUNE_TYPE_MULTIPLIERS",
    "KAGUNE_TYPE_PRIORITY_STAT",
    "resolve_kagune_multiplier",
    "FighterSnapshot",
    "EffectiveStats",
    "StatBreakdown",
    "validate_snapshot",
    "compute_effective_stats",
    "compute_stat_breakdown",
    "Fighter",
]
