import random

import pytest

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
from src.bot.services.chart_game.rounds import Phase, Round, draw_crash

PREPARATION = CHART_CONFIG.preparation_seconds
GROWTH = PREPARATION + CHART_CONFIG.countdown_seconds


class FixedRandom(random.Random):
    def __init__(self, value: float) -> None:
        super().__init__()
        self.value = value

    def random(self) -> float:
        return self.value


def at(multiplier: float) -> float:
    return GROWTH + CHART_CONFIG.seconds_to(multiplier)


@pytest.mark.parametrize(
    ("value", "crash"),
    [(0.0, 100), (0.03, 100), (0.5, 192), (0.9, 960), (0.99, 5000), (0.999999, 5000)],
)
def test_crash_reached_with_return_rate_over_multiplier(value, crash):
    assert draw_crash(FixedRandom(value)) == crash


def test_crash_draws_return_96_percent_on_any_target():
    rng = random.Random(1)
    crashes = [draw_crash(rng) for _ in range(200_000)]

    for target in (150, 200, 500):
        reached = sum(crash >= target for crash in crashes) / len(crashes)
        assert reached * target / 100 == pytest.approx(CHART_CONFIG.return_rate, abs=0.02)


def test_phases_follow_preparation_countdown_growth_and_crash():
    game = Round(crash=241, started_at=0.0)

    assert game.phase(0.0) is Phase.PREPARATION
    assert game.phase(PREPARATION) is Phase.COUNTDOWN
    assert game.phase(GROWTH) is Phase.GROWTH
    assert game.phase(at(2.41)) is Phase.GROWTH
    assert game.phase(at(2.41) + 0.01) is Phase.CRASHED


def test_bets_only_during_preparation_once_per_player():
    game = Round(crash=241, started_at=0.0)
    game.place(1, 1000, None, now=1.0)

    with pytest.raises(ChartAlreadyBet):
        game.place(1, 1000, None, now=2.0)
    with pytest.raises(ChartBetsClosed):
        game.place(2, 1000, None, now=PREPARATION)


@pytest.mark.parametrize("amount", [CHART_CONFIG.min_bet - 1, CHART_CONFIG.max_bet + 1])
def test_bet_amount_limits(amount):
    with pytest.raises(ChartBetOutOfRange):
        Round(crash=241, started_at=0.0).place(1, amount, None, now=0.0)


@pytest.mark.parametrize("target", [100, CHART_CONFIG.max_cents + 1])
def test_target_limits(target):
    with pytest.raises(ChartTargetOutOfRange):
        Round(crash=241, started_at=0.0).place(1, 1000, target, now=0.0)


def test_cash_out_pays_multiplier_at_press_time():
    game = Round(crash=500, started_at=0.0)
    game.place(1, 1000, None, now=0.0)

    bet = game.cash_out(1, now=at(2.41) + 0.001)

    assert (bet.cashed_at, bet.payout) == (241, 2410)
    with pytest.raises(ChartAlreadyCashedOut) as error:
        game.cash_out(1, now=at(3))
    assert error.value.multiplier == 241


def test_cash_out_before_growth_and_after_crash():
    game = Round(crash=241, started_at=0.0)
    game.place(1, 1000, None, now=0.0)

    with pytest.raises(ChartNotGrowing):
        game.cash_out(1, now=PREPARATION + 1)
    with pytest.raises(ChartTooLate) as error:
        game.cash_out(1, now=at(2.41) + 0.01)
    assert error.value.crash == 241
    with pytest.raises(ChartNoBet):
        game.cash_out(2, now=at(2))


def test_press_after_reached_target_reports_auto_cash_out():
    game = Round(crash=500, started_at=0.0)
    game.place(1, 1000, 200, now=0.0)

    with pytest.raises(ChartAlreadyCashedOut) as error:
        game.cash_out(1, now=at(3))
    assert error.value.multiplier == 200


def test_settle_pays_reached_targets_and_loses_the_rest():
    game = Round(crash=241, started_at=0.0)
    game.place(1, 1000, 241, now=0.0)
    game.place(2, 1000, 242, now=0.0)
    game.place(3, 1000, None, now=0.0)

    payouts = {bet.user_id: bet.payout for bet in game.settle()}

    assert payouts == {1: 2410, 2: 0, 3: 0}


def test_cap_cashes_everyone_still_in():
    game = Round(crash=CHART_CONFIG.max_cents, started_at=0.0)
    game.place(1, 1000, None, now=0.0)
    game.place(2, 1000, 300, now=0.0)

    payouts = {bet.user_id: bet.payout for bet in game.settle()}

    assert payouts == {1: 50_000, 2: 3000}


def test_target_changes_only_on_own_bet_during_preparation():
    game = Round(crash=241, started_at=0.0)
    game.place(1, 1000, None, now=0.0)

    assert game.set_target(1, 300, now=1.0).target == 300
    assert game.set_target(1, 150, now=2.0).target == 150
    with pytest.raises(ChartNoBet):
        game.set_target(2, 200, now=2.0)
    with pytest.raises(ChartTargetOutOfRange):
        game.set_target(1, 100, now=2.0)
    with pytest.raises(ChartBetsClosed):
        game.set_target(1, 200, now=PREPARATION)
