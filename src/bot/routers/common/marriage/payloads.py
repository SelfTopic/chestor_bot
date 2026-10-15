from typing import Literal

from selfrot import CallbackPayload


class ProposalPayment(CallbackPayload, prefix="marry_pay"):
    proposer_id: int
    target_id: int


class MarriageAnswer(CallbackPayload, prefix="marry"):
    proposal_id: int
    expected_id: int
    answer: Literal["agree", "decline"]


class FamilyRenameAnswer(CallbackPayload, prefix="fname"):
    rename_id: int
    answer: Literal["agree", "decline"]


class DivorcePress(CallbackPayload, prefix="divorce"):
    expected_id: int
