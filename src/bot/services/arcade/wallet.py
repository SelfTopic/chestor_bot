from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.repositories import (
    BalancesLogRepository,
    ChatRepository,
    GhoulRepository,
    UserCooldownRepository,
    UserRepository,
    WalletRepository,
)

from ..user import UserService


# Автоматы — процессные сервисы со своими сессиями: кошелёк собирается на сессии вызова.
def wallet(session: AsyncSession) -> UserService:
    return UserService(
        UserRepository(session),
        GhoulRepository(session),
        UserCooldownRepository(session),
        ChatRepository(session),
        BalancesLogRepository(session),
        WalletRepository(session),
    )
