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
    duel_id: int
    action: DuelAction
    expected_id: int
