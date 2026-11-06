class LotteryError(Exception): ...


class UnknownLotteryColor(LotteryError):
    def __init__(self, color: str) -> None:
        super().__init__(color)
        self.color = color
