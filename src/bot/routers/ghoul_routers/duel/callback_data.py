from typing import Literal

from selfrot import CallbackPayload

DuelAction = Literal[
    "consent_initiator",
    "consent_target",
    "fora_serious",
    "fora_handicap",
    "outcome_rob",
    "outcome_release",
    "outcome_eat",
]


class DuelPress(CallbackPayload, prefix="duel"):
    """Кнопка дуэли, тот же формат, что у прода: "duel:<id>:<действие>:<чья кнопка>".
    expected_id — кому можно нажать (pressed_by в callbacks.py); вместо ручного
    parse_duel_callback_payload у прода формат и действие проверяет unpack()."""

    duel_id: int
    action: DuelAction
    expected_id: int
