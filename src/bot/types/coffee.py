from dataclasses import dataclass

from src.database.models import Ghoul, User


@dataclass
class CoffeeResult:
    ghoul: Ghoul
    user: User
    award: int
