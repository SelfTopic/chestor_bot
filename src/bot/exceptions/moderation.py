from src.bot.types import ChatRight


class ModerationError(Exception): ...


class AnonymousModerator(ModerationError): ...


class ModeratorLacksRight(ModerationError):
    def __init__(self, right: ChatRight) -> None:
        super().__init__(right.value)
        self.right = right


class BotLacksRight(ModerationError):
    def __init__(self, right: ChatRight) -> None:
        super().__init__(right.value)
        self.right = right


class TargetIsAdmin(ModerationError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


class TargetNotMuted(ModerationError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


class TermOutOfRange(ModerationError):
    def __init__(self, min_seconds: int, max_seconds: int) -> None:
        super().__init__(f"{min_seconds}..{max_seconds}")
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
