import pytest

from src.bot.repositories.balances_log import BalancesLogRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.services.admin.stats_edit import StatsEditService

ADMIN_ID = 1


@pytest.fixture
def stats_service(session):
    return StatsEditService(
        user_repo=UserRepository(session),
        ghoul_repo=GhoulRepository(session),
        balances_log_repo=BalancesLogRepository(session),
    )


async def test_set_user_balance(stats_service, make_user):
    await make_user(telegram_id=400_000_001)
    result = await stats_service.set_stat(
        "400000001", "balance", 9999, admin_id=ADMIN_ID
    )
    assert result.is_ghoul_field is False
    assert result.field == "balance"
    assert result.value == 9999


async def test_set_ghoul_stat(stats_service, make_user, make_ghoul):
    await make_user(telegram_id=400_000_002)
    await make_ghoul(telegram_id=400_000_002)
    result = await stats_service.set_stat(
        "400000002", "strength", 50, admin_id=ADMIN_ID
    )
    assert result.is_ghoul_field is True
    assert result.value == 50


async def test_set_unknown_field_raises(stats_service, make_user):
    await make_user(telegram_id=400_000_003)
    with pytest.raises(ValueError, match="Неизвестное поле"):
        await stats_service.set_stat(
            "400000003", "nonexistent_field", 1, admin_id=ADMIN_ID
        )


async def test_set_stat_unknown_user_raises(stats_service):
    with pytest.raises(ValueError, match="не найден"):
        await stats_service.set_stat("999999999", "balance", 100, admin_id=ADMIN_ID)


async def test_set_ghoul_stat_without_ghoul_raises(stats_service, make_user):
    await make_user(telegram_id=400_000_004)
    with pytest.raises(ValueError, match="профиля гуля"):
        await stats_service.set_stat("400000004", "strength", 10, admin_id=ADMIN_ID)


async def test_resolve_by_username(stats_service, make_user):
    await make_user(telegram_id=400_000_005, username="statuser")
    result = await stats_service.set_stat(
        "@statuser", "balance", 777, admin_id=ADMIN_ID
    )
    assert result.value == 777


def test_format_fields_help(stats_service):
    text = stats_service.format_fields_help()
    assert "balance" in text
    assert "strength" in text


async def test_set_user_balance_writes_audit_log(stats_service, make_user, session):
    from sqlalchemy import select

    from src.database.models import BalancesLog

    await make_user(telegram_id=400_000_006)
    await stats_service.set_stat("400000006", "balance", 500, admin_id=42)

    result = await session.execute(
        select(BalancesLog).filter(BalancesLog.telegram_id == 400_000_006)
    )
    log = result.scalar_one()
    assert log.before_balance == 0
    assert log.after_balance == 500
    assert log.change_balance == 500
    assert "42" in log.log


async def test_set_ghoul_stat_does_not_write_balance_log(
    stats_service, make_user, make_ghoul, session
):
    from sqlalchemy import select

    from src.database.models import BalancesLog

    await make_user(telegram_id=400_000_007)
    await make_ghoul(telegram_id=400_000_007)
    await stats_service.set_stat("400000007", "strength", 50, admin_id=42)

    result = await session.execute(
        select(BalancesLog).filter(BalancesLog.telegram_id == 400_000_007)
    )
    assert result.scalar_one_or_none() is None
