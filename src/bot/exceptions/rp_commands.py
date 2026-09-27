class RpCommandError(Exception): ...


class RpCommandNotFound(RpCommandError):
    def __init__(self, command: str) -> None:
        super().__init__(command)
        self.command = command


class RpCommandLimitReached(RpCommandError):
    def __init__(self, limit: int) -> None:
        super().__init__(limit)
        self.limit = limit
