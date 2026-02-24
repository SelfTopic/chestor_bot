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


async def test_returns_none_for_unknown(lookup_service):
    result = await lookup_service.get_profile("999999999")
    assert result is None


async def test_lookup_by_id(lookup_service, make_user):
    await make_user(telegram_id=500_000_001)
    result = await lookup_service.get_profile("500000001")
    assert result is not None
    assert result.user.telegram_id == 500_000_001
    assert result.ghoul is None


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


async def test_format_profile_banned_user(lookup_service, make_user):
    user = await make_user(telegram_id=500_000_004)
    # Баним напрямую через репо
    repo = lookup_service.user_repo
    await repo.ban(user.telegram_id, reason="тест", banned_until=None)
    profile = await lookup_service.get_profile("500000004")
    text = lookup_service.format_profile(profile)
    assert "Забанен" in text
    assert "тест" in text


async def test_format_profile_active_user(lookup_service, make_user):
    await make_user(telegram_id=500_000_005, username="activeuser")
    profile = await lookup_service.get_profile("500000005")
    text = lookup_service.format_profile(profile)
    assert "Активен" in text
    assert "activeuser" in text
