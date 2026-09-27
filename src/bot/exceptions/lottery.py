class LotteryError(Exception): ...


class BetOutOfRange(LotteryError):
    def __init__(self, min_bet: int, max_bet: int) -> None:
        super().__init__(min_bet, max_bet)
        self.min_bet = min_bet
        self.max_bet = max_bet


class NotEnoughMoneyForBet(LotteryError): ...


class LotteryPlayerMissing(LotteryError): ...


class UnknownLotteryColor(LotteryError):
    def __init__(self, color: str) -> None:
        super().__init__(color)
        self.color = color
