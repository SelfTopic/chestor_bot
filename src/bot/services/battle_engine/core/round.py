from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .actions import RoundAction


@dataclass(frozen=True)
class RoundResult:
    round_number: int
    actions_a: List[RoundAction]
    actions_b: List[RoundAction]
    damage_to_a: float
    damage_to_b: float


__all__ = ["RoundResult"]
