import pytest

from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.services.admin.player_lookup import PlayerLookupService


@pytest.fixture
def lookup_service(session):
    return PlayerLookupService(
        user_repo=UserRepository(session),
        ghoul_repo=GhoulRepository(session),
    )


async def test_lookup_by_username(lookup_service, make_user):
    await make_user(telegram_id=500_000_002, username="lookupuser")
    result = await lookup_service.get_profile("@lookupuser")
    assert result is not None
    assert result.user.username == "lookupuser"


async def test_lookup_includes_ghoul(lookup_service, make_user, make_ghoul):
    await make_user(telegram_id=500_000_003)
    await make_ghoul(telegram_id=500_000_003)
    result = await lookup_service.get_profile("500000003")
    assert result is not None
    assert result.ghoul is not None

