import math
import random
from dataclasses import dataclass, field
from enum import Enum

from src.bot.exceptions import (
    ChartAlreadyBet,
    ChartAlreadyCashedOut,
    ChartBetOutOfRange,
    ChartBetsClosed,
    ChartNoBet,
    ChartNotGrowing,
    ChartTargetOutOfRange,
    ChartTooLate,
)
from src.bot.game_configs import CHART_CONFIG

# Множители хранятся в сотых: x2.41 — 241, чтобы выплаты и сравнения не зависели от float.
ONE = 100


class Phase(Enum):
    PREPARATION = "preparation"
    COUNTDOWN = "countdown"
    GROWTH = "growth"
    CRASHED = "crashed"


def draw_crash(rng: random.Random) -> int:
    reached = CHART_CONFIG.return_rate / (1 - rng.random())
    return min(max(math.floor(reached * ONE), ONE), CHART_CONFIG.max_cents)


@dataclass
class Bet:
    user_id: int
    amount: int
    target: int | None = None
    cashed_at: int | None = None

    @property
    def payout(self) -> int:
        return self.amount * self.cashed_at // ONE if self.cashed_at else 0


@dataclass
class Round:
    crash: int
    started_at: float
    bets: dict[int, Bet] = field(default_factory=dict)

    @property
    def growth_starts_at(self) -> float:
        return self.started_at + CHART_CONFIG.until_growth_seconds

    @property
    def crashes_at(self) -> float:
        return self.growth_starts_at + CHART_CONFIG.seconds_to(self.crash / ONE)

    @property
    def capped(self) -> bool:
        return self.crash == CHART_CONFIG.max_cents

    def phase(self, now: float) -> Phase:
        if now < self.started_at + CHART_CONFIG.preparation_seconds:
            return Phase.PREPARATION
        if now < self.growth_starts_at:
            return Phase.COUNTDOWN
        if now <= self.crashes_at:
            return Phase.GROWTH
        return Phase.CRASHED

    def multiplier(self, now: float) -> int:
        grown = CHART_CONFIG.multiplier(now - self.growth_starts_at)
        return min(math.floor(grown * ONE), self.crash)

    def place(self, user_id: int, amount: int, target: int | None, now: float) -> Bet:
        if self.phase(now) is not Phase.PREPARATION:
            raise ChartBetsClosed()
        if user_id in self.bets:
            raise ChartAlreadyBet()
        if not CHART_CONFIG.min_bet <= amount <= CHART_CONFIG.max_bet:
            raise ChartBetOutOfRange(CHART_CONFIG.min_bet, CHART_CONFIG.max_bet)
        self._check_target(target)
        bet = self.bets[user_id] = Bet(user_id, amount, target)
        return bet

    def set_target(self, user_id: int, target: int, now: float) -> Bet:
        if self.phase(now) is not Phase.PREPARATION:
            raise ChartBetsClosed()
        bet = self.bets.get(user_id)
        if bet is None:
            raise ChartNoBet()
        self._check_target(target)
        bet.target = target
        return bet

    @staticmethod
    def _check_target(target: int | None) -> None:
        min_target = round(CHART_CONFIG.min_target * ONE)
        if target is not None and not min_target <= target <= CHART_CONFIG.max_cents:
            raise ChartTargetOutOfRange(min_target, CHART_CONFIG.max_cents)

    def cash_out(self, user_id: int, now: float) -> Bet:
        bet = self.bets.get(user_id)
        if bet is None:
            raise ChartNoBet()
        phase = self.phase(now)
        if phase in (Phase.PREPARATION, Phase.COUNTDOWN):
            raise ChartNotGrowing()
        multiplier = self.multiplier(now)
        # Цель автовывода могла быть достигнута раньше нажатия: тогда бот уже забрал за игрока.
        if bet.cashed_at is None and bet.target is not None and bet.target <= multiplier:
            bet.cashed_at = bet.target
        if bet.cashed_at is not None:
            raise ChartAlreadyCashedOut(bet.cashed_at)
        if phase is Phase.CRASHED:
            raise ChartTooLate(self.crash)
        bet.cashed_at = multiplier
        return bet

    def settle(self) -> list[Bet]:
        for bet in self.bets.values():
            if bet.cashed_at is not None:
                continue
            if bet.target is not None and bet.target <= self.crash:
                bet.cashed_at = bet.target
            elif self.capped:
                bet.cashed_at = self.crash
        return list(self.bets.values())
