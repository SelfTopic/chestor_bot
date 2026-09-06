import logging
from datetime import timedelta

from src.database.models import Transfer

from ..exceptions import (
    InsufficientBalanceError,
    InvalidTransferAmountError,
    ReceiverLimitExceededError,
    SelfTransferError,
    SenderTooNewError,
)
from ..game_configs import TRANSFER_CONFIG
from ..repositories import BalancesLogRepository, TransferRepository, UserRepository
from ..utils import utcnow_naive

logger = logging.getLogger(__name__)


class TransferService:
    def __init__(
        self,
        user_repository: UserRepository,
        transfer_repository: TransferRepository,
        balances_log_repository: BalancesLogRepository,
    ) -> None:
        self.user_repository = user_repository
        self.transfer_repository = transfer_repository
        self.balances_log_repository = balances_log_repository

    async def validate(self, sender_id: int, receiver_id: int, amount: int) -> None:
        """
        Все проверки ДО списания денег - чтобы никогда не забирать средства
        у отправителя только для того, чтобы потом откатить перевод.

        Raises:
            InvalidTransferAmountError, SelfTransferError, SenderTooNewError,
            ReceiverLimitExceededError
        """
        if amount < TRANSFER_CONFIG.min_amount or amount > TRANSFER_CONFIG.max_amount:
            raise InvalidTransferAmountError(
                f"Сумма перевода должна быть от {TRANSFER_CONFIG.min_amount} "
                f"до {TRANSFER_CONFIG.max_amount}"
            )

        if sender_id == receiver_id:
            raise SelfTransferError()

        sender = await self.user_repository.get(sender_id)
        if not sender:
            raise SenderTooNewError("Отправитель не найден")

        min_age = timedelta(days=TRANSFER_CONFIG.min_sender_account_age_days)
        account_age = utcnow_naive() - sender.created_at
        if account_age < min_age:
            raise SenderTooNewError(
                f"Переводы доступны только аккаунтам старше "
                f"{TRANSFER_CONFIG.min_sender_account_age_days} дн."
            )

        receiver = await self.user_repository.get(receiver_id)
        if not receiver:
            raise SenderTooNewError("Получатель не найден")

        received_last_24h = await self.transfer_repository.count_received_last_24h(
            receiver_id
        )
        if received_last_24h >= TRANSFER_CONFIG.max_received_per_day:
            raise ReceiverLimitExceededError()

    async def transfer(self, sender_id: int, receiver_id: int, amount: int) -> Transfer:
        """
        Выполняет сам перевод. validate() должен быть вызван заранее -
        этот метод не переповторяет проверки лимита/возраста, только
        атомарно двигает деньги и логирует.

        Raises:
            InsufficientBalanceError: если на момент списания баланса не хватило
        """
        sender = await self.user_repository.debit_if_sufficient(sender_id, amount)
        if not sender:
            raise InsufficientBalanceError()

        sender_before = sender.balance + amount
        await self.balances_log_repository.insert(
            telegram_id=sender_id,
            change_balance=-amount,
            before_balance=sender_before,
            after_balance=sender.balance,
            log=f"transfer to {receiver_id}",
        )

        receiver = await self.user_repository.change_balance_atomic(
            receiver_id, delta=amount
        )
        if not receiver:
            # получателя удалили между validate() и этим моментом - поднимаем
            # исключение, чтобы DatabaseMiddleware откатила всю транзакцию
            # целиком (включая уже сделанное списание у отправителя).
            raise InsufficientBalanceError("Получатель не найден, перевод отменён")

        receiver_before = receiver.balance - amount
        await self.balances_log_repository.insert(
            telegram_id=receiver_id,
            change_balance=amount,
            before_balance=receiver_before,
            after_balance=receiver.balance,
            log=f"transfer from {sender_id}",
        )

        return await self.transfer_repository.insert(
            sender_id=sender_id, receiver_id=receiver_id, amount=amount
        )


__all__ = ["TransferService"]
