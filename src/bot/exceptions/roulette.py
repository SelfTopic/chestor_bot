class RouletteError(Exception): ...


class RouletteNoMachine(RouletteError): ...


class RouletteNotYours(RouletteError): ...


class RouletteBusy(RouletteError): ...


class RouletteNoChoice(RouletteError): ...


class RouletteNotEnoughMoney(RouletteError): ...


class RouletteBetOutOfRange(RouletteError):
    def __init__(self, min_bet: int, max_bet: int) -> None:
        super().__init__(min_bet, max_bet)
        self.min_bet = min_bet
        self.max_bet = max_bet


# file_id картинки или ролика устарел: Telegram его больше не принимает, файл надо загрузить заново.
class RouletteStaleMedia(RouletteError): ...
