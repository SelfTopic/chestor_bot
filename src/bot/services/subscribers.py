import time


class SubscriberCache:
    def __init__(self, ttl: float = 600.0) -> None:
        self.ttl = ttl
        self._confirmed_at: dict[int, float] = {}

    def is_fresh(self, telegram_id: int) -> bool:
        confirmed_at = self._confirmed_at.get(telegram_id)
        return confirmed_at is not None and time.monotonic() - confirmed_at < self.ttl

    def confirm(self, telegram_id: int) -> None:
        self._confirmed_at[telegram_id] = time.monotonic()
