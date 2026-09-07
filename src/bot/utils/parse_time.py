from src.bot.types import TimeComponents


def format_duration(total_seconds: int) -> str:
    """Компактная человекочитаемая длительность вида "2д 5ч 30м".

    Секунды не показываются - для таймеров масштаба часов/суток (голод,
    реген) они не нужны. Для коротких кулдаунов, где важны секунды,
    используйте parse_seconds напрямую (см. coffee.py)."""

    if total_seconds <= 0:
        return "0м"

    tc = parse_seconds(total_seconds)

    parts = []
    if tc.days:
        parts.append(f"{tc.days}д")
    if tc.days or tc.hours_remaining:
        parts.append(f"{tc.hours_remaining}ч")
    parts.append(f"{tc.minutes_remaining}м")

    return " ".join(parts)


def parse_seconds(total_seconds: int) -> TimeComponents:
    """Из общего количества секунд даст количество других измерений времени

    Args:
        total_seconds: int - общее количество секунд

    Returns:
        TimeComponents
    """
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
