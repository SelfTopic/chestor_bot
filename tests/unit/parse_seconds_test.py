from src.bot.utils import parse_seconds


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
