from selfrot import InlineKeyboard, button
from selfrot.types import InlineKeyboardMarkup

from src.bot.dialogs import Dialogs
from src.bot.services.dialog import DialogService

from .callback_data import DuelPress

BUTTONS = Dialogs.duel.buttons


def consent_keyboard(
    dialogs: DialogService, duel_id: int, initiator_id: int, target_id: int
) -> InlineKeyboardMarkup:
    return (
        InlineKeyboard()
        .button(
            dialogs.text(BUTTONS.consent_initiator()),
            DuelPress(
                duel_id=duel_id, action="consent_initiator", expected_id=initiator_id
            ),
        )
        .button(
            dialogs.text(BUTTONS.consent_target()),
            DuelPress(duel_id=duel_id, action="consent_target", expected_id=target_id),
        )
        .markup()
    )


def fora_keyboard(
    dialogs: DialogService, duel_id: int, favored_id: int
) -> InlineKeyboardMarkup:
    return (
        InlineKeyboard()
        .row(
            button(
                dialogs.text(BUTTONS.serious()),
                DuelPress(
                    duel_id=duel_id, action="fora_serious", expected_id=favored_id
                ),
            ),
            button(
                dialogs.text(BUTTONS.handicap()),
                DuelPress(
                    duel_id=duel_id, action="fora_handicap", expected_id=favored_id
                ),
            ),
        )
        .markup()
    )


def outcome_keyboard(
    dialogs: DialogService, duel_id: int, winner_id: int
) -> InlineKeyboardMarkup:
    return (
        InlineKeyboard()
        .row(
            button(
                dialogs.text(BUTTONS.rob()),
                DuelPress(duel_id=duel_id, action="outcome_rob", expected_id=winner_id),
            ),
            button(
                dialogs.text(BUTTONS.release()),
                DuelPress(
                    duel_id=duel_id, action="outcome_release", expected_id=winner_id
                ),
            ),
            button(
                dialogs.text(BUTTONS.eat()),
                DuelPress(duel_id=duel_id, action="outcome_eat", expected_id=winner_id),
            ),
        )
        .markup()
    )
