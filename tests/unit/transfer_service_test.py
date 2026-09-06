import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bot.exceptions import (
    InsufficientBalanceError,
    InvalidTransferAmountError,
    ReceiverLimitExceededError,
    SelfTransferError,
    SenderTooNewError,
)
from src.bot.game_configs import TRANSFER_CONFIG
from src.bot.repositories.balances_log import BalancesLogRepository
from src.bot.repositories.transfer import TransferRepository
from src.bot.repositories.user import UserRepository
from src.bot.services.transfer import TransferService
from src.bot.utils import utcnow_naive
from src.database.models import User


async def _age_account(session, telegram_id: int, days: int) -> None:
    """Отодвигает created_at юзера в прошлое, чтобы протестировать возрастной ценз."""
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(created_at=utcnow_naive() - timedelta(days=days))
    )
    await session.commit()


@pytest.fixture
def transfer_service(session):
    return TransferService(
        user_repository=UserRepository(session),
        transfer_repository=TransferRepository(session),
        balances_log_repository=BalancesLogRepository(session),
    )


async def test_resolve_user_by_id(transfer_service, make_user):
    await make_user(telegram_id=42, username="someone")

    user = await transfer_service.resolve_user("42")

    assert user is not None
    assert user.telegram_id == 42


async def test_resolve_user_by_username(transfer_service, make_user):
    await make_user(telegram_id=42, username="someone")

    user = await transfer_service.resolve_user("@someone")

    assert user is not None
    assert user.telegram_id == 42


async def test_resolve_user_not_found(transfer_service):
    user = await transfer_service.resolve_user("@nobody")

    assert user is None


async def test_validate_rejects_amount_out_of_bounds(
    transfer_service, make_user, session
):
    await make_user(telegram_id=1, username="sender")
    await make_user(telegram_id=2, username="receiver")
    await _age_account(session, 1, days=10)

    with pytest.raises(InvalidTransferAmountError):
        await transfer_service.validate(1, 2, 0)

    with pytest.raises(InvalidTransferAmountError):
        await transfer_service.validate(1, 2, TRANSFER_CONFIG.max_amount + 1)


async def test_validate_rejects_self_transfer(transfer_service, make_user, session):
    await make_user(telegram_id=1, username="sender")
    await _age_account(session, 1, days=10)

    with pytest.raises(SelfTransferError):
        await transfer_service.validate(1, 1, 100)


async def test_validate_rejects_too_new_sender(transfer_service, make_user):
    await make_user(telegram_id=1, username="sender")
    await make_user(telegram_id=2, username="receiver")
    # свежесозданный аккаунт, created_at ~ сейчас, младше min_sender_account_age_days

    with pytest.raises(SenderTooNewError):
        await transfer_service.validate(1, 2, 100)


async def test_validate_allows_brand_new_receiver(transfer_service, make_user, session):
    """Возрастной ценз - только для отправителя, получатель может быть новичком."""
    await make_user(telegram_id=1, username="sender")
    await make_user(telegram_id=2, username="receiver")
    await _age_account(session, 1, days=10)

    await transfer_service.validate(1, 2, 100)


async def test_validate_rejects_when_receiver_limit_exceeded(
    transfer_service, make_user, session
):
    await make_user(telegram_id=1, username="sender")
    await make_user(telegram_id=2, username="receiver")
    await _age_account(session, 1, days=10)

    transfer_repo = TransferRepository(session)
    for _ in range(TRANSFER_CONFIG.max_received_per_day):
        await transfer_repo.insert(sender_id=1, receiver_id=2, amount=1)
    await session.commit()

    with pytest.raises(ReceiverLimitExceededError):
        await transfer_service.validate(1, 2, 100)


async def test_transfer_moves_balance_and_logs(transfer_service, make_user, session):
    await make_user(telegram_id=1, username="sender")
    await make_user(telegram_id=2, username="receiver")
    await _age_account(session, 1, days=10)

    user_repo = UserRepository(session)
    await user_repo.change_balance_atomic(1, delta=1000)

    transfer = await transfer_service.transfer(1, 2, 300)

    sender = await user_repo.get(1)
    receiver = await user_repo.get(2)

    assert sender.balance == 700
    assert receiver.balance == 300
    assert transfer.sender_id == 1
    assert transfer.receiver_id == 2
    assert transfer.amount == 300


async def test_transfer_rejects_insufficient_balance(
    transfer_service, make_user, session
):
    await make_user(telegram_id=1, username="sender")
    await make_user(telegram_id=2, username="receiver")
    await _age_account(session, 1, days=10)

    with pytest.raises(InsufficientBalanceError):
        await transfer_service.transfer(1, 2, 500)


async def _transfer_in_own_session(engine, sender_id, receiver_id, amount, results):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        service = TransferService(
            user_repository=UserRepository(session),
            transfer_repository=TransferRepository(session),
            balances_log_repository=BalancesLogRepository(session),
        )
        try:
            await service.transfer(sender_id, receiver_id, amount)
            results.append("ok")
        except InsufficientBalanceError:
            results.append("insufficient")
        await session.commit()


async def test_concurrent_transfers_never_overdraft(engine):
    """
    Регрессия по той же логике, что и общий тест на баланс: debit_if_sufficient
    должен гарантировать, что при куче параллельных списаний с одного счёта
    сумма списанного никогда не превысит реальный баланс, даже если каждое
    отдельное списание по отдельности выглядит допустимым.
    """
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        user_repo = UserRepository(session)
        await user_repo.upsert(telegram_id=1, first_name="Sender")
        await user_repo.upsert(telegram_id=2, first_name="Receiver")
        await _age_account(session, 1, days=10)
        await user_repo.change_balance_atomic(1, delta=1000)
        await session.commit()

    results = []
    await asyncio.gather(
        *[_transfer_in_own_session(engine, 1, 2, 100, results) for _ in range(20)]
    )

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        sender = await UserRepository(session).get(1)
        receiver = await UserRepository(session).get(2)

    assert sender.balance == 0
    assert sender.balance >= 0
    assert receiver.balance == 1000
    assert results.count("ok") == 10
    assert results.count("insufficient") == 10
