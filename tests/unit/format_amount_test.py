from src.bot.utils import format_amount


def test_format_amount_below_thousand_is_unchanged():
    assert format_amount(999) == "999"


def test_format_amount_zero():
    assert format_amount(0) == "0"


def test_format_amount_groups_by_thousands_with_dots():
    assert format_amount(2456789) == "2.456.789"


def test_format_amount_exactly_one_thousand():
    assert format_amount(1000) == "1.000"


def test_format_amount_negative_keeps_sign_before_groups():
    assert format_amount(-2456789) == "-2.456.789"
