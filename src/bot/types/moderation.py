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


class ModerationFeature(str, Enum):
    MUTE = "mute"
    BAN = "ban"
    KICK = "kick"
    WARNS = "warns"
    NOTICES = "notices"


class ChatRight(str, Enum):
    RESTRICT_MEMBERS = "can_restrict_members"
    CHANGE_INFO = "can_change_info"


@dataclass(frozen=True)
class Punishment:
    seconds: Optional[int]
    reason: Optional[str]


# Снимок настроек на начало апдейта: читается и после отката сессии (в on_error), где
# объект из БД уже не загрузить.
@dataclass(frozen=True)
class ChatModeration:
    chat_id: int
    mute_default_seconds: Optional[int]
    ban_default_seconds: Optional[int]
    voice: ModerationVoice
    admin_chat_id: Optional[int]
    admin_chat_request: Optional[int]
    warn_limit: int
    warn_penalty: WarnPenalty
    warn_penalty_seconds: Optional[int]
    warn_expiry_seconds: Optional[int]
    mute_enabled: bool
    ban_enabled: bool
    kick_enabled: bool
    warns_enabled: bool
    notices_enabled: bool

    def enabled(self, feature: ModerationFeature) -> bool:
        return getattr(self, f"{feature.value}_enabled")


@dataclass(frozen=True)
class WarnOutcome:
    count: int
    limit: int
    # Не None — лимит достигнут: наказание и его срок, варны уже сброшены.
    penalty: Optional[WarnPenalty]
    penalty_seconds: Optional[int]
