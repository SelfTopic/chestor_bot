from dataclasses import dataclass
from src.database.models import Ghoul 

from typing import Optional

@dataclass
class RegisterGhoulType:
    """
    The type that the service will return when registering a new ghoul.
    """
    ok: bool 
    is_found: bool 

    ghoul: Optional[Ghoul] = None

__all__ = ["RegisterGhoulType"]