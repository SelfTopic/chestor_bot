from src.bot.types import KaguneType


class GhoulNotFound(Exception):
    def __init__(self, telegram_id: int) -> None:
        super().__init__(telegram_id)
        self.telegram_id = telegram_id


class KaguneNotOwned(Exception):
    def __init__(self, kagune_type: KaguneType) -> None:
        super().__init__(kagune_type)
        self.kagune_type = kagune_type


class KaguneAlreadyOwned(Exception):
    def __init__(self, kagune_type: KaguneType) -> None:
        super().__init__(kagune_type)
        self.kagune_type = kagune_type


class LastKaguneType(Exception): ...
