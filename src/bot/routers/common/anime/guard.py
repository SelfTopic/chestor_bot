import time


class BusyGuard:
    """
    Не больше одной работы на ключ (например, на пользователя) одновременно. Иначе спам
    команды копил бы тяжёлую работу без границ. У записи есть крайний срок: если работа
    не дошла до release (например, упал коммит после хендлера), запись протухает сама и
    не блокирует человека до перезапуска бота.
    """

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._deadlines: dict[int, float] = {}

    def is_busy(self, key: int) -> bool:
        deadline = self._deadlines.get(key)
        return deadline is not None and deadline > time.monotonic()

    def occupy(self, key: int, seconds: float | None = None) -> None:
        """Занять ключ. Вызывать сразу после is_busy, без await между ними."""
        self._deadlines[key] = time.monotonic() + (
            self.seconds if seconds is None else seconds
        )

    def release(self, key: int) -> None:
        self._deadlines.pop(key, None)

    def clear(self) -> None:
        self._deadlines.clear()


# 60 секунд ожидания нарезки плюс запас
cut_guard = BusyGuard(90.0)
