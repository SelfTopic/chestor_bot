import time


class BusyGuard:
    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._deadlines: dict[int, float] = {}

    def is_busy(self, key: int) -> bool:
        deadline = self._deadlines.get(key)
        return deadline is not None and deadline > time.monotonic()

    def occupy(self, key: int, seconds: float | None = None) -> None:
        self._deadlines[key] = time.monotonic() + (
            self.seconds if seconds is None else seconds
        )

    def release(self, key: int) -> None:
        self._deadlines.pop(key, None)

    def clear(self) -> None:
        self._deadlines.clear()


cut_guard = BusyGuard(90.0)
