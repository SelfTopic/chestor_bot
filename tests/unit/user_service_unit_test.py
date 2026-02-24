import pytest

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.user import UserService
from src.bot.types import Race


@pytest.fixture
def user_service(session):
    return UserService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
    )


async def test_get_returns_none_for_unknown_user(user_service):
    result = await user_service.get(find_by=999_999_999)
    assert result is None


async def test_get_by_id(user_service, make_user):
    user = await make_user(telegram_id=100_000_100)
    result = await user_service.get(find_by=100_000_100)
    assert result is not None
    assert result.telegram_id == user.telegram_id


async def test_get_by_username(user_service, make_user):
    await make_user(telegram_id=100_000_101, username="uniqueuser")
    result = await user_service.get(find_by="uniqueuser")
    assert result is not None
    assert result.username == "uniqueuser"


async def test_plus_balance(user_service, make_user):
    await make_user(telegram_id=100_000_200)
    result = await user_service.plus_balance(
        telegram_id=100_000_200, change_balance=500
    )
    assert result.balance == 500


async def test_plus_balance_accumulates(user_service, make_user):
    await make_user(telegram_id=100_000_201)
    await user_service.plus_balance(telegram_id=100_000_201, change_balance=100)
    result = await user_service.plus_balance(
        telegram_id=100_000_201, change_balance=200
    )
    assert result.balance == 300


async def test_minus_balance(user_service, make_user):
    await make_user(telegram_id=100_000_202)
    await user_service.plus_balance(telegram_id=100_000_202, change_balance=1000)
    result = await user_service.minus_balance(
        telegram_id=100_000_202, change_balance=400
    )
    assert result.balance == 600


async def test_minus_balance_can_go_negative(user_service, make_user):
    """Сервис не запрещает уход в минус — это ответственность вызывающего кода."""
    await make_user(telegram_id=100_000_203)
    result = await user_service.minus_balance(
        telegram_id=100_000_203, change_balance=100
    )
    assert result.balance == -100


async def test_plus_balance_raises_for_unknown_user(user_service):
    with pytest.raises(ValueError):
        await user_service.plus_balance(telegram_id=999_999_001, change_balance=100)


async def test_race_returns_correct_enum(user_service):
    ghoul_bit = Race.GHOUL.value["bit"]
    result = user_service.race(ghoul_bit)
    assert result == Race.GHOUL


async def test_race_returns_none_for_unknown_bit(user_service):
    result = user_service.race(999)
    assert result is None


async def test_get_top_balance(user_service, make_user):
    await make_user(telegram_id=100_000_300)
    await make_user(telegram_id=100_000_301, username="rich")
    await user_service.plus_balance(telegram_id=100_000_301, change_balance=9999)
    top = await user_service.get_top_balance(limit=5)
    assert len(top) >= 1
    assert top[0].balance >= top[-1].balance
