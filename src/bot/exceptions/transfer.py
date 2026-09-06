class TransferError(Exception):
    """Common base class for transfer errors"""

    def __init__(self, message: str = "Перевод не выполнен") -> None:
        super().__init__(message)


class InvalidTransferAmountError(TransferError):
    def __init__(self, message: str = "Некорректная сумма перевода") -> None:
        super().__init__(message)


class SelfTransferError(TransferError):
    def __init__(self, message: str = "Нельзя перевести деньги самому себе") -> None:
        super().__init__(message)


class InsufficientBalanceError(TransferError):
    def __init__(self, message: str = "Недостаточно средств для перевода") -> None:
        super().__init__(message)


class SenderTooNewError(TransferError):
    def __init__(
        self, message: str = "Аккаунт отправителя слишком новый для переводов"
    ) -> None:
        super().__init__(message)


class ReceiverLimitExceededError(TransferError):
    def __init__(
        self,
        message: str = "Этот аккаунт уже получил слишком много переводов за последние сутки",
    ) -> None:
        super().__init__(message)


__all__ = [
    "TransferError",
    "InvalidTransferAmountError",
    "SelfTransferError",
    "InsufficientBalanceError",
    "SenderTooNewError",
    "ReceiverLimitExceededError",
]
