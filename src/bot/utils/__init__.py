from .kagune_calculate import calculate_kagune
from .level_progress_calculate import apply_level_progress, level_progress_bar
from .parse_time import format_duration, parse_seconds
from .regen_calculate import (
    apply_hunger_restore,
    compute_health,
    compute_hunger,
    effective_regeneration,
    get_hunger_tier,
    health_regen_per_hour,
    hours_until_full_health,
    hours_until_hunger_threshold,
    hours_until_starved,
    next_hunger_threshold,
)
from .time_now import utcnow_naive

__all__ = [
    "calculate_kagune",
    "apply_level_progress",
    "level_progress_bar",
    "parse_seconds",
    "format_duration",
    "apply_hunger_restore",
    "compute_health",
    "compute_hunger",
    "effective_regeneration",
    "get_hunger_tier",
    "health_regen_per_hour",
    "hours_until_full_health",
    "hours_until_hunger_threshold",
    "hours_until_starved",
    "next_hunger_threshold",
    "utcnow_naive",
]
