from enum import Enum


class ModerationVoice(str, Enum):
    NEUTRAL = "neutral"
    ROUGH = "rough"


class ModerationActionType(str, Enum):
    MUTE = "mute"
    UNMUTE = "unmute"
    BAN = "ban"
    UNBAN = "unban"
    KICK = "kick"
