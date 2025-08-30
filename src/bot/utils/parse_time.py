from src.bot.types import TimeComponents


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
        seconds_remaining=seconds_remaining
    )