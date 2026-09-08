from src.bot.routers.ghoul_routers.upgrade_kagune import parse_kagune_callback_payload


def test_parse_kagune_callback_payload_valid():
    assert parse_kagune_callback_payload("123456789_bikaku") == (123456789, "bikaku")


def test_parse_kagune_callback_payload_rejects_missing_underscore():
    assert parse_kagune_callback_payload("bikaku") is None


def test_parse_kagune_callback_payload_rejects_non_numeric_invoker_id():
    """Регрессия по существу самой правки: если invoker_id нельзя разобрать
    как число, доверять ему для сверки личности нельзя вообще."""
    assert parse_kagune_callback_payload("not_a_number_bikaku") is None


def test_parse_kagune_callback_payload_empty_string():
    assert parse_kagune_callback_payload("") is None
