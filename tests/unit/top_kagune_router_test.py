from src.bot.routers.ghoul_routers.tops import (
    _build_top_kagune_keyboard,
    parse_top_kagune_callback_payload,
)


def test_parse_top_kagune_callback_payload_valid():
    assert parse_top_kagune_callback_payload("20_sum_ukaku") == (20, "sum", "ukaku")


def test_parse_top_kagune_callback_payload_rejects_missing_parts():
    assert parse_top_kagune_callback_payload("20_sum") is None


def test_parse_top_kagune_callback_payload_rejects_non_numeric_count():
    assert parse_top_kagune_callback_payload("abc_sum_ukaku") is None


def test_parse_top_kagune_callback_payload_rejects_unknown_view():
    assert parse_top_kagune_callback_payload("20_sum_notarealtype") is None


def test_build_top_kagune_keyboard_excludes_current_view():
    keyboard = _build_top_kagune_keyboard(current="sum", previous=None, count=20)
    labels = [b.text for row in keyboard.inline_keyboard for b in row]

    assert len(labels) == 4  # 5 видов минус текущий
    assert "Сумма" not in labels


def test_build_top_kagune_keyboard_marks_previous_view():
    keyboard = _build_top_kagune_keyboard(current="ukaku", previous="sum", count=20)
    labels = [b.text for row in keyboard.inline_keyboard for b in row]

    assert "⬅️ Сумма" in labels
    assert "Сумма" not in labels  # не должно остаться немаркированной версии
    assert "Коукаку" in labels  # остальные виды - как обычно, без стрелки


def test_build_top_kagune_keyboard_no_previous_marker_when_none():
    """Первый показ топа (по текстовой команде) - без "предыдущего" вида,
    ни одна кнопка не должна быть помечена стрелкой."""
    keyboard = _build_top_kagune_keyboard(current="sum", previous=None, count=20)
    labels = [b.text for row in keyboard.inline_keyboard for b in row]

    assert not any(label.startswith("⬅️") for label in labels)


def test_build_top_kagune_keyboard_callback_data_encodes_transition():
    keyboard = _build_top_kagune_keyboard(current="sum", previous=None, count=15)
    button = next(
        b
        for row in keyboard.inline_keyboard
        for b in row
        if b.text == "Укаку"
    )
    assert button.callback_data == "topkagune_15_sum_ukaku"
