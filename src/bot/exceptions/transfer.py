class TransferError(Exception): ...


class InvalidTransferAmountError(TransferError):
    def __init__(self, min_amount: int, max_amount: int) -> None:
        super().__init__(min_amount, max_amount)
        self.min_amount = min_amount
        self.max_amount = max_amount


class SelfTransferError(TransferError): ...


class SenderMissingError(TransferError): ...


class SenderTooNewError(TransferError):
    def __init__(self, min_age_days: int) -> None:
        super().__init__(min_age_days)
        self.min_age_days = min_age_days


class InsufficientBalanceError(TransferError): ...


class ReceiverMissingError(TransferError): ...


class ReceiverVanishedError(TransferError): ...


class ReceiverLimitExceededError(TransferError): ...


__all__ = [
    "TransferError",
    "InvalidTransferAmountError",
    "SelfTransferError",
    "SenderMissingError",
    "SenderTooNewError",
    "InsufficientBalanceError",
    "ReceiverMissingError",
    "ReceiverVanishedError",
    "ReceiverLimitExceededError",
]
