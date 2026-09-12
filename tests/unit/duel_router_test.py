from src.bot.routers.ghoul_routers.duel import parse_duel_callback_payload


def test_parse_duel_callback_payload_valid_consent():
    assert parse_duel_callback_payload("duel:42:consent_initiator:123456789") == (
        42,
        "consent_initiator",
        123456789,
    )


def test_parse_duel_callback_payload_valid_outcome():
    assert parse_duel_callback_payload("duel:1:outcome_eat:987") == (1, "outcome_eat", 987)


def test_parse_duel_callback_payload_rejects_wrong_prefix():
    assert parse_duel_callback_payload("notduel:1:consent_initiator:1") is None


def test_parse_duel_callback_payload_rejects_missing_parts():
    assert parse_duel_callback_payload("duel:1:consent_initiator") is None


def test_parse_duel_callback_payload_rejects_non_numeric_duel_id():
    assert parse_duel_callback_payload("duel:abc:consent_initiator:123") is None


def test_parse_duel_callback_payload_rejects_non_numeric_expected_id():
    """Регрессия по существу самой проверки: если expected_telegram_id
    нельзя разобрать как число, доверять ему для сверки личности нельзя."""
    assert parse_duel_callback_payload("duel:1:consent_initiator:not_a_number") is None


def test_parse_duel_callback_payload_rejects_unknown_action():
    assert parse_duel_callback_payload("duel:1:self_destruct:123") is None


def test_parse_duel_callback_payload_empty_string():
    assert parse_duel_callback_payload("") is None
