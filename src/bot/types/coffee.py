from dataclasses import dataclass

from src.database.models import Ghoul


@dataclass
class CoffeeResult:
    ghoul: Ghoul
    balance: int
    award: int
