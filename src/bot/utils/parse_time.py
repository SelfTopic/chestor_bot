from typing import Literal

from src.bot.types import TimeComponents

TimeUnit = Literal["months", "days", "hours", "minutes"]
TimeParts = list[tuple[int, TimeUnit]]


def duration_parts(total_seconds: int) -> TimeParts:
    if total_seconds <= 0:
        return [(0, "minutes")]

    tc = parse_seconds(total_seconds)

    parts: TimeParts = []
    if tc.days:
        parts.append((tc.days, "days"))
    if tc.days or tc.hours_remaining:
        parts.append((tc.hours_remaining, "hours"))
    parts.append((tc.minutes_remaining, "minutes"))
    return parts


DAY = 24 * 3600
MONTH = 30 * DAY


# Две старшие единицы: «1мес 10д», «5д 4ч», «2ч 15м» — точнее для стажа не нужно.
def age_parts(total_seconds: int) -> TimeParts:
    seconds = max(0, total_seconds)
    units: TimeParts = [
        (seconds // MONTH, "months"),
        (seconds % MONTH // DAY, "days"),
        (seconds % DAY // 3600, "hours"),
        (seconds % 3600 // 60, "minutes"),
    ]
    first = next((i for i, (value, _) in enumerate(units) if value), len(units) - 1)
    return [(value, unit) for value, unit in units[first : first + 2] if value] or [
        (0, "minutes")
    ]


def parse_seconds(total_seconds: int) -> TimeComponents:
    total_minutes = total_seconds // 60
    total_hours = total_seconds // 3600

    days = total_seconds // (24 * 3600)
    remainder_after_days = total_seconds % (24 * 3600)

    hours_remaining = remainder_after_days // 3600
    remainder_after_hours = remainder_after_days % 3600

    minutes_remaining = remainder_after_hours // 60
    seconds_remaining = remainder_after_hours % 60

    return TimeComponents(
        days=days,
        hours_remaining=hours_remaining,
        total_hours=total_hours,
        minutes_remaining=minutes_remaining,
        total_minutes=total_minutes,
        seconds_remaining=seconds_remaining,
        total_seconds=total_seconds,
    )
