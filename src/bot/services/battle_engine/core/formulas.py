from __future__ import annotations

import random
from enum import Enum
from typing import TYPE_CHECKING

from ....game_configs import BATTLE_CONFIG

if TYPE_CHECKING:
    from .fighter import EffectiveStats

_default_rng = random.Random()


class AttackType(Enum):
    PHYSICAL = "physical"
    KAGUNE = "kagune"


_DODGE_FLOOR = 5.0
_DODGE_CEILING = 95.0
_DODGE_BASE_SCALE = 90.0
_DODGE_BASE_DIVISOR = 10000.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _compress_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 1.0 if numerator <= 0 else float("inf")
    if numerator <= 0:
        return 0.0
    return (numerator / denominator) ** BATTLE_CONFIG.stat_sensitivity_exponent


def compress_stat_advantage(own: float, other: float) -> float:
    if own <= other or other <= 0:
        return own
    return other * _compress_ratio(own, other)


def _dodge_base(dexterity: float) -> float:
    return _clamp(
        _DODGE_FLOOR + (dexterity / _DODGE_BASE_DIVISOR) * _DODGE_BASE_SCALE,
        _DODGE_FLOOR,
        _DODGE_CEILING,
    )


def dodge_chance(defender_dexterity: float, attacker_dexterity: float) -> float:
    weaker = min(defender_dexterity, attacker_dexterity)
    stronger = max(defender_dexterity, attacker_dexterity)
    base = _dodge_base(weaker)

    if defender_dexterity <= attacker_dexterity:
        return base
    return _clamp(base * _compress_ratio(stronger, weaker), _DODGE_FLOOR, _DODGE_CEILING)


def extra_hit_percent(speed_defender: float, speed_attacker: float) -> float:
    hi = max(speed_attacker, speed_defender)
    lo = min(speed_attacker, speed_defender)
    if hi <= 0:
        return 0.0

    compressed_hi = lo * _compress_ratio(hi, lo) if lo > 0 else hi
    diff_ratio = (compressed_hi - lo) / compressed_hi
    if speed_attacker >= speed_defender:
        return diff_ratio * 200.0
    return diff_ratio * 100.0


def resolve_hit_chain(percent: float, rng: random.Random) -> int:
    guaranteed = 0
    remaining = percent
    while remaining > 100.0:
        remaining -= 100.0
        guaranteed += 1

    if rng.random() * 100.0 < remaining:
        guaranteed += 1

    return guaranteed


def resolve_extra_hit_counts(
    speed_a: float, speed_b: float, rng: random.Random
) -> tuple[int, int]:
    pct_a = extra_hit_percent(speed_defender=speed_b, speed_attacker=speed_a)
    pct_b = extra_hit_percent(speed_defender=speed_a, speed_attacker=speed_b)
    return resolve_hit_chain(pct_a, rng), resolve_hit_chain(pct_b, rng)


def attack_type_chance(physical_hits_landed: int) -> float:
    return max(
        0.0,
        100.0 - BATTLE_CONFIG.physical_attack_decay_percent * physical_hits_landed,
    )


def kagune_gate_chance(defender_dex_speed: float, attacker_dex_speed: float) -> float:
    if attacker_dex_speed <= 0:
        return 100.0
    return min(
        100.0,
        BATTLE_CONFIG.kagune_gate_base_percent
        * _compress_ratio(defender_dex_speed, attacker_dex_speed),
    )


def resolve_block_percent(
    kagune_up: bool,
    attack_type: AttackType,
    attacker: "EffectiveStats",
    defender: "EffectiveStats",
    rng: random.Random,
) -> float:
    if kagune_up:
        if attack_type is AttackType.PHYSICAL:
            return rng.uniform(
                BATTLE_CONFIG.physical_block_min, BATTLE_CONFIG.physical_block_max
            )
        margin = defender.kagune_strength - attacker.kagune_strength
        if margin >= 0:
            return rng.uniform(
                BATTLE_CONFIG.modest_block_min, BATTLE_CONFIG.modest_block_max
            )
        return 0.0

    if attack_type is AttackType.PHYSICAL:
        margin = defender.health - attacker.health
        if margin >= 0:
            return rng.uniform(
                BATTLE_CONFIG.modest_block_min, BATTLE_CONFIG.modest_block_max
            )
        return 0.0

    return 0.0


def _compressed_damage_stat(
    attack_type: AttackType, attacker: "EffectiveStats", defender: "EffectiveStats"
) -> float:
    if attack_type is AttackType.PHYSICAL:
        own, other = attacker.strength, defender.strength
    else:
        own = attacker.strength + attacker.kagune_strength
        other = defender.strength + defender.kagune_strength

    return compress_stat_advantage(own, other)


def raw_damage(
    attack_type: AttackType,
    attacker: "EffectiveStats",
    defender: "EffectiveStats",
    rng: random.Random,
) -> float:
    variance = rng.uniform(
        BATTLE_CONFIG.damage_variance_min, BATTLE_CONFIG.damage_variance_max
    )
    return variance * _compressed_damage_stat(attack_type, attacker, defender)


def raw_fast_attack_damage(
    attack_type: AttackType,
    attacker: "EffectiveStats",
    defender: "EffectiveStats",
    rng: random.Random,
) -> float:
    variance = rng.uniform(
        BATTLE_CONFIG.fast_attack_damage_variance_min,
        BATTLE_CONFIG.fast_attack_damage_variance_max,
    )
    return variance * _compressed_damage_stat(attack_type, attacker, defender)


def regen_proc_chance(own_regeneration: float, opponent_regeneration: float) -> float:
    hi = max(own_regeneration, opponent_regeneration)
    lo = min(own_regeneration, opponent_regeneration)
    if hi <= 0:
        return 0.0

    compressed_hi = lo * _compress_ratio(hi, lo) if lo > 0 else hi
    diff_ratio = (compressed_hi - lo) / compressed_hi
    if own_regeneration >= opponent_regeneration:
        return min(100.0, diff_ratio * 200.0)
    return diff_ratio * 100.0


__all__ = [
    "AttackType",
    "compress_stat_advantage",
    "dodge_chance",
    "extra_hit_percent",
    "resolve_hit_chain",
    "resolve_extra_hit_counts",
    "attack_type_chance",
    "kagune_gate_chance",
    "resolve_block_percent",
    "raw_damage",
    "raw_fast_attack_damage",
    "regen_proc_chance",
]
