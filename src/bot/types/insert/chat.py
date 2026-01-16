from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ChatInsert:
    telegram_id: int
    title: Optional[str] 
    username: Optional[str]
    creator_id: Optional[int]

__all__ = ["ChatInsert"]