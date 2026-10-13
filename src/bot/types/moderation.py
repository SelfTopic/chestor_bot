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
    WARN = "warn"
    UNWARN = "unwarn"


class WarnPenalty(str, Enum):
    MUTE = "mute"
    BAN = "ban"
    KICK = "kick"


class ChatRight(str, Enum):
    RESTRICT_MEMBERS = "can_restrict_members"
    CHANGE_INFO = "can_change_info"


@dataclass(frozen=True)
class Punishment:
    seconds: Optional[int]
    reason: Optional[str]


@dataclass(frozen=True)
class WarnOutcome:
    count: int
    limit: int
    # Не None — лимит достигнут: наказание и его срок, варны уже сброшены.
    penalty: Optional[WarnPenalty]
    penalty_seconds: Optional[int]
