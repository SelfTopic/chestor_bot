"""Результат одного раунда - см. actions.py про то, почему это список
действий на участника, а не одно поле."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .actions import RoundAction


@dataclass(frozen=True)
class RoundResult:
    round_number: int
    actions_a: List[RoundAction]  # порядок: основное действие первым, бонусные FastAttack - следом
    actions_b: List[RoundAction]
    damage_to_a: float  # сумма урона из всех hit-содержащих действий в actions_b
    damage_to_b: float


__all__ = ["RoundResult"]
