from datetime import datetime, timedelta, timezone

import pytest

from src.bot.repositories.user import UserRepository
from src.bot.services.admin.ban import BanService


@pytest.fixture
def ban_service(session):
    return BanService(user_repo=UserRepository(session))


async def test_parse_duration_minutes(ban_service):
    result = ban_service.parse_duration("30m")
    assert result is not None
    diff = result - datetime.now(timezone.utc)
    assert timedelta(minutes=29) < diff < timedelta(minutes=31)


async def test_parse_duration_hours(ban_service):
    result = ban_service.parse_duration("24h")
    assert result is not None


async def test_parse_duration_days(ban_service):
    result = ban_service.parse_duration("7d")
    assert result is not None


async def test_parse_duration_invalid_returns_none(ban_service):
    assert ban_service.parse_duration("навсегда") is None
    assert ban_service.parse_duration("abc") is None
    assert ban_service.parse_duration("7x") is None


async def test_ban_duration_unknown_falls_into_reason(ban_service, make_user):
    """Нераспознанная длительность должна стать частью причины."""
    await make_user(telegram_id=300_000_004, username="reasontest")
    result = await ban_service.ban("reasontest", duration_str="навсегда", reason=None)
    assert result.banned_until is None
    assert "навсегда" in (result.reason or "")
