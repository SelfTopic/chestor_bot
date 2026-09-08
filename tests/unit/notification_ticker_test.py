import pytest

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.scheduled_notification import ScheduledNotificationRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.dialog import DialogService
from src.bot.services.ghoul import GhoulService
from src.bot.services.notification_ticker import NotificationTicker
from src.bot.types import NotificationType
from src.database.models import ScheduledNotification


class FakeBot:
    def __init__(self):
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str):
        self.sent.append((chat_id, text))


@pytest.fixture
def fake_bot():
    return FakeBot()


@pytest.fixture
def ticker(fake_bot):
    return NotificationTicker(bot=fake_bot, dialog_service=DialogService())


@pytest.fixture
def notification_repository(session):
    return ScheduledNotificationRepository(session)


@pytest.fixture
def ghoul_service(session, notification_repository):
    return GhoulService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
        notification_repository=notification_repository,
    )


def _due_row(telegram_id, notification_type, threshold=None):
    return ScheduledNotification(
        telegram_id=telegram_id, notification_type=notification_type, threshold=threshold
    )


async def test_handle_due_sends_health_full_message(
    ticker, fake_bot, ghoul_service, notification_repository, make_user, make_ghoul
):
    await make_user(telegram_id=600_000_001)
    await make_ghoul(telegram_id=600_000_001, health=10, max_health=10)

    row = _due_row(600_000_001, NotificationType.HEALTH_FULL)
    await ticker._handle_due(row, ghoul_service, notification_repository)

    assert len(fake_bot.sent) == 1
    chat_id, text = fake_bot.sent[0]
    assert chat_id == 600_000_001
    assert "восстановил здоровье" in text


async def test_handle_due_skips_health_full_if_no_longer_true(
    ticker, fake_bot, ghoul_service, notification_repository, make_user, make_ghoul
):
    """Между постановкой пуша и тиком гуль мог потерять здоровье (бой) -
    отправлять устаревшее "здоровье полное" нельзя."""
    await make_user(telegram_id=600_000_002)
    await make_ghoul(telegram_id=600_000_002, health=1, max_health=10)

    row = _due_row(600_000_002, NotificationType.HEALTH_FULL)
    await ticker._handle_due(row, ghoul_service, notification_repository)

    assert fake_bot.sent == []


async def test_handle_due_sends_hunger_threshold_message(
    ticker, fake_bot, ghoul_service, notification_repository, make_user, make_ghoul
):
    await make_user(telegram_id=600_000_003)
    await make_ghoul(telegram_id=600_000_003, hunger=70)

    row = _due_row(600_000_003, NotificationType.HUNGER_THRESHOLD, threshold=75)
    await ticker._handle_due(row, ghoul_service, notification_repository)

    assert len(fake_bot.sent) == 1
    _, text = fake_bot.sent[0]
    assert "75" in text


async def test_handle_due_sends_hunger_zero_placeholder_message(
    ticker, fake_bot, ghoul_service, notification_repository, make_user, make_ghoul
):
    await make_user(telegram_id=600_000_004)
    await make_ghoul(telegram_id=600_000_004, hunger=0)

    row = _due_row(600_000_004, NotificationType.HUNGER_THRESHOLD, threshold=0)
    await ticker._handle_due(row, ghoul_service, notification_repository)

    assert len(fake_bot.sent) == 1
    _, text = fake_bot.sent[0]
    assert "0%" in text
    assert "заглушка" in text


async def test_handle_due_skips_hunger_threshold_if_already_eaten(
    ticker, fake_bot, ghoul_service, notification_repository, make_user, make_ghoul
):
    await make_user(telegram_id=600_000_005)
    await make_ghoul(telegram_id=600_000_005, hunger=90)  # уже выше порога 75

    row = _due_row(600_000_005, NotificationType.HUNGER_THRESHOLD, threshold=75)
    await ticker._handle_due(row, ghoul_service, notification_repository)

    assert fake_bot.sent == []


async def test_handle_due_cleans_up_missing_ghoul(
    ticker, fake_bot, ghoul_service, notification_repository, session
):
    row = _due_row(999_999_999, NotificationType.HEALTH_FULL)
    await ticker._handle_due(row, ghoul_service, notification_repository)

    assert fake_bot.sent == []
