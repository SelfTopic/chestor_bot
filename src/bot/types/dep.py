from dataclasses import dataclass
from enum import Enum


class DepColor(Enum):
    RED = "красный"
    BLUE = "синий"
    GREEN = "зелёный"
    WHITE = "белый"
    YELLOW = "жёлтый"


@dataclass
class DepResult:
    balance: int
    bet_amount: int
    chosen_color: DepColor
    winning_color: DepColor
    is_won: bool
    earned: int
    video_file_id: str | None = None
