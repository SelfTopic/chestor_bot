from typing import Literal

from selfrot import CallbackPayload


class PromoCardPress(CallbackPayload, prefix="promo_card"):
    promo_id: int
    action: Literal["show", "delete", "confirm", "cancel"] = "show"
    page: int = 0
