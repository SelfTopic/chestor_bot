import pytest

from src.bot.utils import age_parts, duration_parts, parse_seconds


def test_parse_seconds_basic():
    tc = parse_seconds(total_seconds=3661)
    assert tc.total_hours == 1
    assert tc.hours_remaining == 1
    assert tc.minutes_remaining == 1
    assert tc.seconds_remaining == 1


def test_parse_seconds_exact_day_boundary():
    """При total_seconds == ровно 24ч hours_remaining обнуляется (это остаток
    после вычитания дней), а total_hours остаётся корректным. Роутеры,
    которые не показывают дни в сообщении, обязаны использовать total_hours,
    иначе кулдаун на ровно сутки отображается как "0 часов, 0 минут и 0 секунд".
    """
    tc = parse_seconds(total_seconds=86400)
    assert tc.days == 1
    assert tc.hours_remaining == 0
    assert tc.total_hours == 24
    assert tc.minutes_remaining == 0
    assert tc.seconds_remaining == 0


def test_parse_seconds_beyond_a_day():
    tc = parse_seconds(total_seconds=90000)  # 25h
    assert tc.hours_remaining == 1
    assert tc.total_hours == 25


def test_duration_parts_minutes_only():
    assert duration_parts(300) == [(5, "minutes")]


def test_duration_parts_hours_and_minutes():
    assert duration_parts(3661) == [(1, "hours"), (1, "minutes")]


def test_duration_parts_days_hours_minutes():
    assert duration_parts(90000) == [(1, "days"), (1, "hours"), (0, "minutes")]  # 25h


def test_duration_parts_non_positive_clamped():
    assert duration_parts(0) == [(0, "minutes")]
    assert duration_parts(-10) == [(0, "minutes")]


@pytest.mark.parametrize(
    ("seconds", "age"),
    [
        (-5, [(0, "minutes")]),
        (59, [(0, "minutes")]),
        (7 * 60, [(7, "minutes")]),
        (2 * 3600 + 15 * 60, [(2, "hours"), (15, "minutes")]),
        (5 * 86400 + 4 * 3600 + 59 * 60, [(5, "days"), (4, "hours")]),
        (40 * 86400 + 12 * 3600, [(1, "months"), (10, "days")]),
        (30 * 86400 + 5 * 3600, [(1, "months")]),
    ],
)
def test_age_keeps_the_two_largest_units(seconds, age):
    assert age_parts(seconds) == age
