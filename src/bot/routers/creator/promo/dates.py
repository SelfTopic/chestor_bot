from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MOSCOW = ZoneInfo("Europe/Moscow")


def moscow_time(naive_utc: datetime) -> str:
    return naive_utc.replace(tzinfo=timezone.utc).astimezone(MOSCOW).strftime("%d.%m.%Y %H:%M")
