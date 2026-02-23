from dataclasses import dataclass
from enum import Enum

from src.database.models import Ghoul, User


class DepColor(Enum):
    RED = "красный"
    BLUE = "синий"
    GREEN = "зелёный"
    WHITE = "белый"
    YELLOW = "жёлтый"


@dataclass
class DepResult:
    ghoul: Ghoul
    user: User
    bet_amount: int
    chosen_color: DepColor
    winning_color: DepColor
    is_won: bool
    earned: int
    video_file_id: str | None = None
