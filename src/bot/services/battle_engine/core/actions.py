from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .hit import HitResult


class RoundActionType(Enum):
    ATTACK = "attack"
    REGEN = "regen"
    DEFENSE = "defense"
    IDLE = "idle"


@dataclass(frozen=True)
class AttackAction:
    hit: "HitResult"


@dataclass(frozen=True)
class FastAttackAction:
    hit: "HitResult"


@dataclass(frozen=True)
class RegenAction:
    healed: float
    was_guaranteed: bool


@dataclass(frozen=True)
class DefenseAction:
    pass
@dataclass(frozen=True)
class IdleAction:
    pass
RoundAction = Union[AttackAction, FastAttackAction, RegenAction, DefenseAction, IdleAction]


__all__ = [
    "RoundActionType",
    "AttackAction",
    "FastAttackAction",
    "RegenAction",
    "DefenseAction",
    "IdleAction",
    "RoundAction",
]
