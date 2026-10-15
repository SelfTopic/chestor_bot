import logging
from datetime import timedelta
from typing import Optional

from src.database.models import Transfer, User

from ..exceptions import (
    InsufficientBalanceError,
    InvalidTransferAmountError,
    ReceiverLimitExceededError,
    ReceiverMissingError,
    ReceiverVanishedError,
    SelfTransferError,
    SenderMissingError,
    SenderTooNewError,
    SpouseTransferError,
)
from ..game_configs import TRANSFER_CONFIG
from ..repositories import (
    BalancesLogRepository,
    FamilyRepository,
    TransferRepository,
    UserRepository,
    WalletRepository,
)
from ..utils import utcnow_naive

logger = logging.getLogger(__name__)


class TransferService:
    def __init__(
        self,
        user_repository: UserRepository,
        transfer_repository: TransferRepository,
        balances_log_repository: BalancesLogRepository,
        wallet_repository: WalletRepository,
        family_repository: FamilyRepository,
    ) -> None:
        self.user_repository = user_repository
        self.transfer_repository = transfer_repository
        self.balances_log_repository = balances_log_repository
        self.wallet_repository = wallet_repository
        self.family_repository = family_repository

    async def resolve_user(self, query: str) -> Optional[User]:
        search = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
        return await self.user_repository.get(search)

    async def validate(self, sender_id: int, receiver_id: int, amount: int) -> None:
        if amount < TRANSFER_CONFIG.min_amount or amount > TRANSFER_CONFIG.max_amount:
            raise InvalidTransferAmountError(
                TRANSFER_CONFIG.min_amount, TRANSFER_CONFIG.max_amount
            )

        if sender_id == receiver_id:
            raise SelfTransferError()

        if await self.family_repository.same_family(sender_id, receiver_id):
            raise SpouseTransferError()

        sender = await self.user_repository.get(sender_id)
        if not sender:
            raise SenderMissingError()

        min_age = timedelta(days=TRANSFER_CONFIG.min_sender_account_age_days)
        account_age = utcnow_naive() - sender.created_at
        if account_age < min_age:
            raise SenderTooNewError(TRANSFER_CONFIG.min_sender_account_age_days)

        if (await self.wallet_repository.balance(sender_id) or 0) < amount:
            # Ранняя проверка, чтобы не гонять человека по подтверждениям зря; источник
            # истины — атомарное списание в transfer().
            raise InsufficientBalanceError()

        receiver = await self.user_repository.get(receiver_id)
        if not receiver:
            raise ReceiverMissingError()

        received_last_24h = await self.transfer_repository.count_received_last_24h(
            receiver_id
        )
        if received_last_24h >= TRANSFER_CONFIG.max_received_per_day:
            raise ReceiverLimitExceededError()

    async def transfer(self, sender_id: int, receiver_id: int, amount: int) -> Transfer:
        sender_after = await self.wallet_repository.debit_if_sufficient(sender_id, amount)
        if sender_after is None:
            raise InsufficientBalanceError()

        await self.balances_log_repository.insert(
            telegram_id=sender_id,
            change_balance=-amount,
            before_balance=sender_after + amount,
            after_balance=sender_after,
            log=f"transfer to {receiver_id}",
        )

        receiver_after = await self.wallet_repository.change(receiver_id, amount)
        if receiver_after is None:
            # Получателя удалили после validate(): исключение откатит всю транзакцию вместе
            # со списанием.
            raise ReceiverVanishedError()

        await self.balances_log_repository.insert(
            telegram_id=receiver_id,
            change_balance=amount,
            before_balance=receiver_after - amount,
            after_balance=receiver_after,
            log=f"transfer from {sender_id}",
        )

        return await self.transfer_repository.insert(
            sender_id=sender_id, receiver_id=receiver_id, amount=amount
        )


__all__ = ["TransferService"]
