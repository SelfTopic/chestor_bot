from enum import Enum


class NotificationType(str, Enum):
    HEALTH_FULL = "health_full"
    HUNGER_THRESHOLD = "hunger_threshold"
