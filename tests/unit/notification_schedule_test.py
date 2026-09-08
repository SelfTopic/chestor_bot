import pytest
from sqlalchemy import select

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.scheduled_notification import ScheduledNotificationRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.ghoul import GhoulService
from src.bot.types import NotificationType
from src.bot.utils import utcnow_naive
from src.database.models import ScheduledNotification


@pytest.fixture
def ghoul_service(session):
    return GhoulService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
        notification_repository=ScheduledNotificationRepository(session),
    )


async def _get_notification(session, telegram_id: int, notification_type: str):
    result = await session.execute(
        select(ScheduledNotification).where(
            ScheduledNotification.telegram_id == telegram_id,
            ScheduledNotification.notification_type == notification_type,
        )
    )
    return result.scalar_one_or_none()


async def test_get_schedules_health_full_when_not_full(
    ghoul_service, make_user, make_ghoul, session
):
    await make_user(telegram_id=500_000_001)
    await make_ghoul(
        telegram_id=500_000_001, health=1, max_health=10, regeneration=5, hunger=100
    )

    ghoul = await ghoul_service.get(500_000_001)
    assert ghoul is not None

    row = await _get_notification(
        session, 500_000_001, NotificationType.HEALTH_FULL
    )
    assert row is not None
    # 9 HP не хватает, 5 HP/ч -> 1.8ч
    assert row.fire_at > utcnow_naive()


async def test_get_deletes_health_full_when_already_full(
    ghoul_service, make_user, make_ghoul, session
):
    await make_user(telegram_id=500_000_002)
    await make_ghoul(
        telegram_id=500_000_002, health=10, max_health=10, regeneration=5, hunger=100
    )

    await ghoul_service.get(500_000_002)

    row = await _get_notification(
        session, 500_000_002, NotificationType.HEALTH_FULL
    )
    assert row is None


async def test_get_schedules_next_hunger_threshold(
    ghoul_service, make_user, make_ghoul, session
):
    await make_user(telegram_id=500_000_003)
    await make_ghoul(telegram_id=500_000_003, hunger=80)

    await ghoul_service.get(500_000_003)

    row = await _get_notification(
        session, 500_000_003, NotificationType.HUNGER_THRESHOLD
    )
    assert row is not None
    assert row.threshold == 75


async def test_get_schedules_death_alarm_when_hunger_is_zero(
    ghoul_service, make_user, make_ghoul, session
):
    """При hunger=0 больше нет "порогов ниже" в обычном смысле, но строка не
    удаляется - планируется с threshold=-1 (будильник на момент потенциальной
    смерти). Без этого неактивный игрок, застрявший на 0%, был бы бессмертен."""
    await make_user(telegram_id=500_000_004)
    await make_ghoul(telegram_id=500_000_004, hunger=0)

    await ghoul_service.get(500_000_004)

    row = await _get_notification(
        session, 500_000_004, NotificationType.HUNGER_THRESHOLD
    )
    assert row is not None
    assert row.threshold == -1


async def test_eat_human_reschedules_hunger_threshold(
    ghoul_service, make_user, make_ghoul, session
):
    await make_user(telegram_id=500_000_005)
    await make_ghoul(telegram_id=500_000_005, hunger=20)  # ближайший порог - 0

    row_before = await _get_notification(
        session, 500_000_005, NotificationType.HUNGER_THRESHOLD
    )
    assert row_before is None  # ещё не читали гуля ни разу - расписания нет

    await ghoul_service.eat_human(500_000_005)

    row_after = await _get_notification(
        session, 500_000_005, NotificationType.HUNGER_THRESHOLD
    )
    assert row_after is not None
    # после еды голод точно вырос выше 20, порог должен пересчитаться
    assert row_after.threshold in (75, 50, 25, 0)


async def test_sync_upserts_not_duplicates_on_repeated_calls(
    ghoul_service, make_user, make_ghoul, session
):
    """Одна строка на (telegram_id, notification_type), не история - повторный
    вызов должен ПЕРЕСТАВИТЬ существующую запись, а не добавить вторую."""
    await make_user(telegram_id=500_000_007)
    await make_ghoul(
        telegram_id=500_000_007, health=1, max_health=10, regeneration=5, hunger=80
    )

    await ghoul_service.get(500_000_007)
    await ghoul_service.get(500_000_007)
    await ghoul_service.get(500_000_007)

    result = await session.execute(
        select(ScheduledNotification).where(
            ScheduledNotification.telegram_id == 500_000_007
        )
    )
    rows = result.scalars().all()
    types = [r.notification_type for r in rows]
    assert types.count(NotificationType.HEALTH_FULL) == 1
    assert types.count(NotificationType.HUNGER_THRESHOLD) == 1


async def test_ghoul_service_without_notification_repository_does_not_schedule(
    make_user, make_ghoul, session
):
    """Опциональность notification_repository не должна ронять обычный get()."""
    plain_ghoul_service = GhoulService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
    )

    await make_user(telegram_id=500_000_006)
    await make_ghoul(telegram_id=500_000_006, health=1, max_health=10)

    ghoul = await plain_ghoul_service.get(500_000_006)
    assert ghoul is not None

    row = await _get_notification(
        session, 500_000_006, NotificationType.HEALTH_FULL
    )
    assert row is None
