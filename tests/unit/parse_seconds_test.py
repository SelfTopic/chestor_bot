from src.bot.utils import format_duration, parse_seconds


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


def test_format_duration_minutes_only():
    assert format_duration(300) == "5м"


def test_format_duration_hours_and_minutes():
    assert format_duration(3661) == "1ч 1м"


def test_format_duration_days_hours_minutes():
    assert format_duration(90000) == "1д 1ч 0м"  # 25h


def test_format_duration_non_positive_clamped():
    assert format_duration(0) == "0м"
    assert format_duration(-10) == "0м"
