import logging
from typing import Optional, Union

from src.database.models import User

from ..repositories import (
    BalancesLogRepository,
    ChatRepository,
    GhoulRepository,
    UserCooldownRepository,
    TopWallet,
    UserRepository,
    WalletRepository,
)
from ..types import Race
from .base import Base

logger = logging.getLogger(__name__)


class UserService(Base):
    def __init__(
        self,
        user_repository: UserRepository,
        ghoul_repository: GhoulRepository,
        user_cooldown_repository: UserCooldownRepository,
        chat_repository: ChatRepository,
        balances_log_repository: BalancesLogRepository,
        wallet_repository: WalletRepository,
    ) -> None:
        super().__init__(
            user_repository=user_repository,
            ghoul_repository=ghoul_repository,
            user_cooldown_repository=user_cooldown_repository,
            chat_repository=chat_repository,
        )
        self.balances_log_repository = balances_log_repository
        self.wallet_repository = wallet_repository

    async def get(self, find_by: Union[str, int]) -> Optional[User]:
        logger.debug(f"Called method get. Search parameter: {find_by}")

        user = await self.user_repository.get(search_parameter=find_by)

        logger.debug(f"User found: {user is not None}")
        return user

    async def balance(self, telegram_id: int) -> int:
        balance = await self.wallet_repository.balance(telegram_id)
        return 0 if balance is None else balance

    async def plus_balance(self, telegram_id: int, change_balance: int, log: str) -> int:
        return await self._change(telegram_id, change_balance, log)

    async def minus_balance(self, telegram_id: int, change_balance: int, log: str) -> int:
        return await self._change(telegram_id, -change_balance, log)

    async def _change(self, telegram_id: int, delta: int, log: str) -> int:
        logger.debug(f"Balance change. User ID: {telegram_id}, delta: {delta}")

        after = await self.wallet_repository.change(telegram_id, delta)
        if after is None:
            logger.error("Cannot change balance to nouser")
            raise ValueError("Cannot change balance to nouser")

        await self._log(telegram_id, delta, after, log)
        return after

    async def debit_if_sufficient(self, telegram_id: int, amount: int, log: str) -> int | None:
        after = await self.wallet_repository.debit_if_sufficient(telegram_id, amount)
        if after is not None:
            await self._log(telegram_id, -amount, after, log)
        return after

    async def _log(self, telegram_id: int, delta: int, after: int, log: str) -> None:
        await self.balances_log_repository.insert(
            telegram_id=telegram_id,
            change_balance=delta,
            before_balance=after - delta,
            after_balance=after,
            log=log,
        )

    async def get_top_balance(self, limit: int = 20) -> list[TopWallet]:
        return await self.wallet_repository.top(limit)

    def race(self, bit: int) -> Optional[Race]:
        for race in Race:
            if race.value["bit"] == bit:
                return race

        return None


__all__ = ["UserService"]
