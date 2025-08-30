from dataclasses import dataclass

@dataclass
class TimeComponents:
    days: int
    hours_remaining: int
    total_hours: int
    minutes_remaining: int
    total_minutes: int
    seconds_remaining: int

