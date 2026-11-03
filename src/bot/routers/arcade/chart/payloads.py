from selfrot import CallbackPayload


class BetPress(CallbackPayload, prefix="chart_bet"):
    amount: int


class TargetPress(CallbackPayload, prefix="chart_target"):
    target: int


class CashOutPress(CallbackPayload, prefix="chart_cash"):
    pass
