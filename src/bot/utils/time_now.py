from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """Naive UTC-время, совместимое с колонками DateTime() без timezone=True."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
