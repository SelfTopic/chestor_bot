class ChartError(Exception): ...


class ChartBetsClosed(ChartError): ...


class ChartAlreadyBet(ChartError): ...


class ChartBetOutOfRange(ChartError):
    def __init__(self, min_bet: int, max_bet: int) -> None:
        super().__init__(min_bet, max_bet)
        self.min_bet = min_bet
        self.max_bet = max_bet


class ChartTargetOutOfRange(ChartError):
    def __init__(self, min_target: int, max_target: int) -> None:
        super().__init__(min_target, max_target)
        self.min_target = min_target
        self.max_target = max_target


class ChartNotGrowing(ChartError): ...


class ChartNoBet(ChartError): ...


class ChartAlreadyCashedOut(ChartError):
    def __init__(self, multiplier: int) -> None:
        super().__init__(multiplier)
        self.multiplier = multiplier


class ChartTooLate(ChartError):
    def __init__(self, crash: int) -> None:
        super().__init__(crash)
        self.crash = crash
