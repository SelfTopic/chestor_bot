from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TypeRpCommandEnum(Enum):
    TEXT = "text"
    PHOTO = "photo"
    ANIMATION = "animation"


@dataclass
class RpCommandDTO:
    id: int
    chat_id: int
    command: str
    action: str
    type_command: TypeRpCommandEnum
    file_id: str | None
    created_at: datetime
