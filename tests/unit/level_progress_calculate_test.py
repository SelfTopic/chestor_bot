import pytest

from src.bot.utils import apply_level_progress


def test_apply_level_progress_simple_gain_no_levelup():
    progress, levels = apply_level_progress(current_progress=50.0, delta=30.0)
    assert progress == 80.0
    assert levels == 0


def test_apply_level_progress_exact_100_triggers_one_levelup():
    progress, levels = apply_level_progress(current_progress=90.0, delta=10.0)
    assert progress == 0.0
    assert levels == 1


def test_apply_level_progress_overflow_discards_excess_not_carries():
    """Уровень не должен перепрыгивать значения - излишек выше 100%
    отбрасывается, прогресс сбрасывается ровно в 0, а не в остаток."""
    progress, levels = apply_level_progress(current_progress=90.0, delta=15.0)
    assert progress == 0.0
    assert levels == 1


def test_apply_level_progress_huge_gain_still_gives_only_one_levelup():
    """Принятая эмерджентная механика - большой k за один бой может дать
    прирост намного выше 100%, но уровень всё равно поднимается максимум на
    1 за раз, весь излишек просто теряется. См. BATTLE_DESIGN.md."""
    progress, levels = apply_level_progress(current_progress=0.0, delta=250.0)
    assert progress == 0.0
    assert levels == 1


def test_apply_level_progress_negative_delta_reduces_progress():
    progress, levels = apply_level_progress(current_progress=50.0, delta=-20.0)
    assert progress == 30.0
    assert levels == 0


def test_apply_level_progress_negative_delta_clamps_at_zero():
    progress, levels = apply_level_progress(current_progress=50.0, delta=-100.0)
    assert progress == 0.0
    assert levels == 0


def test_apply_level_progress_fractional_values():
    progress, levels = apply_level_progress(current_progress=99.5, delta=0.6)
    assert progress == 0.0
    assert levels == 1


def test_apply_level_progress_fractional_values_without_levelup():
    progress, levels = apply_level_progress(current_progress=99.5, delta=0.4)
    assert progress == pytest.approx(99.9)
    assert levels == 0
