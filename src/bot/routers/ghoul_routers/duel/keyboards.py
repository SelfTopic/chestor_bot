from selfrot import InlineKeyboard, button
from selfrot.types import InlineKeyboardMarkup

from .callback_data import DuelPress


def consent_keyboard(
    duel_id: int, initiator_id: int, target_id: int
) -> InlineKeyboardMarkup:
    """Две отдельные кнопки: сама команда "дуэль" ещё не согласие, нужно явное
    подтверждение обеих сторон."""
    return (
        InlineKeyboard()
        .button(
            "✅ Подтверждаю вызов (инициатор)",
            DuelPress(
                duel_id=duel_id, action="consent_initiator", expected_id=initiator_id
            ),
        )
        .button(
            "⚔️ Принимаю бой",
            DuelPress(duel_id=duel_id, action="consent_target", expected_id=target_id),
        )
        .markup()
    )


def fora_keyboard(duel_id: int, favored_id: int) -> InlineKeyboardMarkup:
    return (
        InlineKeyboard()
        .row(
            button(
                "⚔️ Всерьёз",
                DuelPress(
                    duel_id=duel_id, action="fora_serious", expected_id=favored_id
                ),
            ),
            button(
                "🤝 Дать фору",
                DuelPress(
                    duel_id=duel_id, action="fora_handicap", expected_id=favored_id
                ),
            ),
        )
        .markup()
    )


def outcome_keyboard(duel_id: int, winner_id: int) -> InlineKeyboardMarkup:
    return (
        InlineKeyboard()
        .row(
            button(
                "💰 Ограбить",
                DuelPress(duel_id=duel_id, action="outcome_rob", expected_id=winner_id),
            ),
            button(
                "🕊️ Отпустить",
                DuelPress(
                    duel_id=duel_id, action="outcome_release", expected_id=winner_id
                ),
            ),
            button(
                "🍖 Съесть",
                DuelPress(duel_id=duel_id, action="outcome_eat", expected_id=winner_id),
            ),
        )
        .markup()
    )
