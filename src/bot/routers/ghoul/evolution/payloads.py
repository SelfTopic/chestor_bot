from selfrot import CallbackPayload


class BuyKagunePress(CallbackPayload, prefix="evo_kagune"):
    invoker_id: int


class BecomeKakujaPress(CallbackPayload, prefix="evo_kakuja"):
    invoker_id: int
