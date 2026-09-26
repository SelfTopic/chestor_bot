from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .formulas import (
    AttackType,
    attack_type_chance,
    dodge_chance,
    kagune_gate_chance,
    raw_damage,
    raw_fast_attack_damage,
    resolve_block_percent,
)

if TYPE_CHECKING:
    from .fighter import Fighter

_default_rng = random.Random()


@dataclass(frozen=True)
class HitResult:
    landed: bool
    attack_type: Optional[AttackType] = None
    kagune_up: Optional[bool] = None
    block_percent: float = 0.0
    damage: float = 0.0
    dodge_chance_used: float = 0.0
    gate_chance_used: float = 0.0
    physical_chance_used: float = 0.0


def resolve_hit(
    attacker: "Fighter",
    defender: "Fighter",
    rng: random.Random = _default_rng,
    is_fast_attack: bool = False,
) -> HitResult:
    a, d = attacker.stats, defender.stats

    dodge = dodge_chance(d.dexterity, a.dexterity)
    if rng.random() * 100.0 < dodge:
        return HitResult(landed=False, dodge_chance_used=dodge)

    gate = kagune_gate_chance(d.dexterity + d.speed, a.dexterity + a.speed)
    kagune_up = rng.random() * 100.0 < gate

    physical_chance = attack_type_chance(attacker.physical_streak)
    if rng.random() * 100.0 < physical_chance:
        attack_type = AttackType.PHYSICAL
        attacker.physical_streak += 1
    else:
        attack_type = AttackType.KAGUNE

    block_percent = resolve_block_percent(kagune_up, attack_type, a, d, rng)
    raw = (
        raw_fast_attack_damage(attack_type, a, d, rng)
        if is_fast_attack
        else raw_damage(attack_type, a, d, rng)
    )
    damage = raw * (1 - block_percent / 100.0)

    return HitResult(
        landed=True,
        attack_type=attack_type,
        kagune_up=kagune_up,
        block_percent=block_percent,
        damage=damage,
        dodge_chance_used=dodge,
        gate_chance_used=gate,
        physical_chance_used=physical_chance,
    )


__all__ = ["HitResult", "resolve_hit"]
