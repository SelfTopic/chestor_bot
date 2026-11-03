from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ..arcade.media import Media
from .spins import Choice, Outcome


class Stage(Enum):
    READY = "ready"
    SPINNING = "spinning"
    CLOSED = "closed"


# Что показать в сообщении автомата. outcome — итог последнего прокрута (в SPINNING — того,
# что крутится сейчас: экран не должен показывать его до остановки ленты); message_id нет —
# сообщение ещё не отправлено.
@dataclass(frozen=True)
class Screen:
    stage: Stage
    machine_id: int
    chat_id: int
    user_id: int
    message_id: int | None
    media: Media
    choice: Choice
    balance: int
    outcome: Outcome | None = None


@dataclass(frozen=True)
class Shown:
    message_id: int
    file_id: str | None


class RouletteScreen(Protocol):
    async def show(self, screen: Screen) -> Shown: ...

    # Надпись на картинке на языке чата знает только экран.
    async def closed_picture(self, chat_id: int, position: int) -> bytes: ...
