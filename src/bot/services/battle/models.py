from dataclasses import dataclass
from typing import Literal, Optional, Tuple

from src.bot.types import KaguneType

EventType = Literal[
    "intro",
    "pause",
    "hit",
    "miss",
    "block",
    "crit",
    "regen",
    "outro",
    "turn",
]

KAGUNE_COLORS: dict[KaguneType, Tuple[int, int, int]] = {
    KaguneType.UKAKU: (220, 50, 50),
    KaguneType.KOUKAKU: (50, 120, 220),
    KaguneType.RINKAKU: (150, 50, 220),
    KaguneType.BIKAKU: (220, 150, 30),
}


@dataclass
class BattleFighter:
    name: str
    hp: int
    max_hp: int
    kagune_type: KaguneType
    hp_delta_attacker: int = 0
    hp_delta_defender: int = 0

    strength: int = 1
    dexterity: int = 1
    speed: int = 1
    kagune_strength: int = 1
    regeneration: int = 1

    regen_used: bool = False

    @property
    def color(self) -> Tuple[int, int, int]:
        return KAGUNE_COLORS[self.kagune_type]

    @property
    def hp_ratio(self) -> float:
        return max(0.0, self.hp / self.max_hp)


@dataclass
class BattleEvent:
    type: EventType
    attacker: BattleFighter
    defender: BattleFighter
    damage: int
    defender_hp_before: int
    defender_hp_after: int
    attacker_hp_before: int = 0
    attacker_hp_after: int = 0
    attacker_hp_snapshot: int = 0
    hp_delta_attacker: int = 0
    hp_delta_defender: int = 0


@dataclass
class TimelineEventData:
    left: BattleFighter
    right: BattleFighter

    left_hp_before: int
    right_hp_before: int

    left_hp_after: int
    right_hp_after: int

    attacker_left: Optional[bool] = None
    battle_event: Optional[BattleEvent] = None
    winner: Optional[BattleFighter] = None
    is_draw: Optional[bool] = None


@dataclass
class TimelineEvent:
    type: str
    duration: Optional[float]
    data: TimelineEventData
    battle_event: Optional[BattleEvent] = None
