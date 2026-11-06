from selfrot import CallbackPayload


class ColorPress(CallbackPayload, prefix="roulette_color"):
    machine: int
    color: int


class AmountPress(CallbackPayload, prefix="roulette_amount"):
    machine: int
    amount: int


class SpinPress(CallbackPayload, prefix="roulette_spin"):
    machine: int


class HintPress(CallbackPayload, prefix="roulette_hint"):
    color: bool
