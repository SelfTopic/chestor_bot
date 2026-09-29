from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ModerationVoice(str, Enum):
    NEUTRAL = "neutral"
    ROUGH = "rough"


class ModerationActionType(str, Enum):
    MUTE = "mute"
    UNMUTE = "unmute"
    BAN = "ban"
    UNBAN = "unban"
    KICK = "kick"


class ChatRight(str, Enum):
    RESTRICT_MEMBERS = "can_restrict_members"


@dataclass(frozen=True)
class Punishment:
    seconds: Optional[int]
    reason: Optional[str]
