from dataclasses import dataclass
from typing import Optional

from src.database.models import Ghoul


@dataclass
class RegisterGhoulType:
    ok: bool 
    is_found: bool 

    ghoul: Optional[Ghoul] = None

__all__ = ["RegisterGhoulType"]