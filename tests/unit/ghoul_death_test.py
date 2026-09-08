from datetime import timedelta

import pytest
from sqlalchemy import select

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.death_log import DeathLogRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.scheduled_notification import ScheduledNotificationRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.ghoul import GhoulService
from src.bot.types import KaguneType, NotificationType
from src.bot.utils import utcnow_naive
from src.database.models import DeathLog, ScheduledNotification


@pytest.fixture
def death_log_repository(session):
    return DeathLogRepository(session)


@pytest.fixture
def notification_repository(session):
    return ScheduledNotificationRepository(session)


@pytest.fixture
def ghoul_service(session, death_log_repository, notification_repository):
    return GhoulService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
        notification_repository=notification_repository,
        death_log_repository=death_log_repository,
    )


async def test_apply_death_sets_is_dead_and_increments_deaths(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=800_000_001)
    await make_ghoul(telegram_id=800_000_001, deaths=2)

    updated = await ghoul_service.apply_death(800_000_001, cause="starvation")

    assert updated.is_dead is True
    assert updated.deaths == 3


async def test_apply_death_writes_death_log_snapshot(
    ghoul_service, make_user, make_ghoul, session
):
    await make_user(telegram_id=800_000_002)
    await make_ghoul(
        telegram_id=800_000_002, level=7, lifetime_rc_earned=123
    )

    await ghoul_service.apply_death(800_000_002, cause="starvation")

    result = await session.execute(
        select(DeathLog).where(DeathLog.telegram_id == 800_000_002)
    )
    log = result.scalar_one()
    assert log.cause == "starvation"
    assert log.level == 7
    assert log.lifetime_rc_earned == 123
    assert log.killer_telegram_id is None


async def test_apply_death_records_killer_when_eaten(
    ghoul_service, make_user, make_ghoul, session
):
    await make_user(telegram_id=800_000_003)
    await make_ghoul(telegram_id=800_000_003)

    await ghoul_service.apply_death(
        800_000_003, cause="eaten", killer_telegram_id=800_000_099
    )

    result = await session.execute(
        select(DeathLog).where(DeathLog.telegram_id == 800_000_003)
    )
    log = result.scalar_one()
    assert log.cause == "eaten"
    assert log.killer_telegram_id == 800_000_099


async def test_apply_death_schedules_death_notification(
    ghoul_service, make_user, make_ghoul, notification_repository, session
):
    await make_user(telegram_id=800_000_004)
    await make_ghoul(telegram_id=800_000_004)

    await ghoul_service.apply_death(800_000_004, cause="starvation")

    result = await session.execute(
        select(ScheduledNotification).where(
            ScheduledNotification.telegram_id == 800_000_004,
            ScheduledNotification.notification_type == NotificationType.DEATH,
        )
    )
    assert result.scalar_one_or_none() is not None


async def test_apply_death_clears_hunger_and_health_pushes(
    ghoul_service, make_user, make_ghoul, session
):
    await make_user(telegram_id=800_000_005)
    ghoul = await make_ghoul(telegram_id=800_000_005, hunger=50, health=1, max_health=10)

    # снапшот, как это обычно происходит при обычном чтении
    await ghoul_service.sync_notification_schedule(ghoul, now=utcnow_naive())

    await ghoul_service.apply_death(800_000_005, cause="starvation")

    result = await session.execute(
        select(ScheduledNotification).where(
            ScheduledNotification.telegram_id == 800_000_005,
            ScheduledNotification.notification_type.in_(
                [NotificationType.HEALTH_FULL, NotificationType.HUNGER_THRESHOLD]
            ),
        )
    )
    assert result.scalars().all() == []


async def test_materialize_passive_stats_skips_dead_ghoul(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=800_000_006)
    ghoul = await make_ghoul(
        telegram_id=800_000_006, is_dead=True, hunger=0, health=1, max_health=10
    )

    result = await ghoul_service.materialize_passive_stats(ghoul)

    assert result is ghoul  # ничего не пересчитано и не сохранено


async def test_materialize_passive_stats_triggers_death_on_starvation(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=800_000_007)
    ghoul = await make_ghoul(
        telegram_id=800_000_007,
        hunger=1,
        hunger_updated_at=utcnow_naive() - timedelta(hours=168 * 10),
    )

    result = await ghoul_service.materialize_passive_stats(ghoul)

    assert result.is_dead is True


async def test_reset_for_rebirth_keeps_survivors_and_resets_rest(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=800_000_008)
    ghoul = await make_ghoul(
        telegram_id=800_000_008,
        deaths=3,
        is_dead=True,
        level=10,
        level_progress=55.0,
        rc_money=500,
        lifetime_rc_earned=500,
        strength=99,
        hunger=1,
        health=1,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=42,
    )
    original_id = ghoul.id
    original_created_at = ghoul.created_at

    reborn = await ghoul_service.reset_for_rebirth(800_000_008)

    assert reborn.id == original_id
    assert reborn.created_at == original_created_at
    assert reborn.deaths == 3  # пережил сброс
    assert reborn.is_dead is False
    assert reborn.level == 1
    assert reborn.level_progress == 0.0
    assert reborn.rc_money == 0
    assert reborn.lifetime_rc_earned == 0
    assert reborn.strength == 1
    assert reborn.hunger == 100
    assert reborn.health == 5


async def test_reset_for_rebirth_grants_exactly_one_new_kagune_type(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=800_000_009)
    await make_ghoul(
        telegram_id=800_000_009,
        is_dead=True,
        kagune_type_bit=KaguneType.UKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"],
        kagune_strength_ukaku=10,
        kagune_strength_bikaku=20,
    )

    reborn = await ghoul_service.reset_for_rebirth(800_000_009)

    owned = ghoul_service.owned_kagune_types(reborn)
    assert len(owned) == 1
    assert ghoul_service.get_kagune_strength(reborn, owned[0]) == 1
