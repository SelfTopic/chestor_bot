import asyncio

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.user import UserService


async def _plus_balance_in_own_session(
    engine: AsyncEngine, telegram_id: int, amount: int
):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        service = UserService(
            UserRepository(session),
            GhoulRepository(session),
            UserCooldownRepository(session),
            ChatRepository(session),
        )
        await service.plus_balance(telegram_id=telegram_id, change_balance=amount)
        await session.commit()


async def test_concurrent_plus_balance_does_not_lose_updates(engine):
    """
    Регрессия: plus_balance/minus_balance раньше читали баланс, считали новое
    значение в питоне и писали абсолютное число - под конкурентной нагрузкой
    (несколько Telegram-обновлений одного юзера обрабатываются одновременно)
    часть обновлений тихо терялась, хотя каждая строка лога выглядела верной.
    """
    telegram_id = 500_000_001

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        await UserRepository(session).upsert(
            telegram_id=telegram_id, first_name="RaceTest"
        )
        await session.commit()

    concurrent_updates = 20
    amount = 10

    await asyncio.gather(
        *[
            _plus_balance_in_own_session(engine, telegram_id, amount)
            for _ in range(concurrent_updates)
        ]
    )

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get(telegram_id)

    assert user is not None
    assert user.balance == concurrent_updates * amount
