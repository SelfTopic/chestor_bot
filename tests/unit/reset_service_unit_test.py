import pytest

from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.services.admin.reset import ResetService


@pytest.fixture
def reset_service(session):
    return ResetService(
        user_repo=UserRepository(session),
        ghoul_repo=GhoulRepository(session),
    )


async def test_reset_user_deletes_both(reset_service, make_user, make_ghoul, session):
    await make_user(telegram_id=600_000_003)
    await make_ghoul(telegram_id=600_000_003)

    result = await reset_service.reset_user("600000003")
    assert result.user_deleted is True
    assert result.ghoul_deleted is True

    user_repo = UserRepository(session)
    user = await user_repo.get(600_000_003)
    assert user is None


async def test_reset_unknown_user_raises(reset_service):
    with pytest.raises(ValueError, match="не найден"):
        await reset_service.reset_user("999999888")


