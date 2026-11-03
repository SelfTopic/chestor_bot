from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .rounds import Bet
from .videos import Media


class Stage(Enum):
    PREPARATION = "preparation"
    GROWTH = "growth"
    CLOSED = "closed"
    ABANDONED = "abandoned"


@dataclass(frozen=True)
class BetLine:
    telegram_id: int
    amount: int
    target: int | None
    cashed_at: int | None
    payout: int

    @classmethod
    def of(cls, bet: Bet) -> "BetLine":
        return cls(bet.user_id, bet.amount, bet.target, bet.cashed_at, bet.payout)


# Что показать в сообщении автомата. В подготовке и после закрытия bets — итоги прошлого
# раунда (crash — его обвал), в росте — ставки текущего. message_id нет — сообщение ещё не
# отправлено; history нет — раундов ещё не было; panel — картинка ставок раунда.
@dataclass(frozen=True)
class Screen:
    stage: Stage
    chat_id: int
    message_id: int | None
    media: Media
    history: Media | None
    bets: list[BetLine]
    crash: int | None = None
    closes_in: float = 0.0
    panel: Media | None = None


@dataclass(frozen=True)
class Shown:
    message_id: int
    file_id: str | None


class MachineScreen(Protocol):
    async def show(self, screen: Screen) -> Shown: ...

    # Картинка ставок: имена и подписи на языке чата знает только экран.
    async def bets_picture(self, chat_id: int, bets: list[BetLine]) -> bytes: ...
