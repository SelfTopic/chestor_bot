import pytest

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.death_log import DeathLogRepository
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
        self.sent_video: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str):
        self.sent.append((chat_id, text))

    async def send_video(self, chat_id: int, video, caption: str):
        self.sent_video.append((chat_id, caption))

        class _FakeMessage:
            video = None

        return _FakeMessage()


class FakeMediaService:
    """Ничего не загружено - как в реальности, пока никто не выполнил
    /add_gif death. get_random_gif/get_random_video ведут себя одинаково -
    оба просто возвращают None, ничего не создавая на диске."""

    async def get_random_video(self, collection_string: str, user_id: int):
        return None


@pytest.fixture
def fake_bot():
    return FakeBot()


@pytest.fixture
def fake_media_service():
    return FakeMediaService()


@pytest.fixture
def ticker(fake_bot):
    return NotificationTicker(bot=fake_bot, dialog_service=DialogService())


@pytest.fixture
def notification_repository(session):
    return ScheduledNotificationRepository(session)


@pytest.fixture
def death_log_repository(session):
    return DeathLogRepository(session)


@pytest.fixture
def ghoul_service(session, notification_repository, death_log_repository):
    return GhoulService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
        notification_repository=notification_repository,
        death_log_repository=death_log_repository,
    )


def _due_row(telegram_id, notification_type, threshold=None):
    return ScheduledNotification(
        telegram_id=telegram_id, notification_type=notification_type, threshold=threshold
    )


async def _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                   fake_media_service):
    await ticker._handle_due(
        row, ghoul_service, notification_repository, death_log_repository, fake_media_service
    )


async def test_handle_due_sends_health_full_message(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, make_user, make_ghoul,
):
    await make_user(telegram_id=600_000_001)
    await make_ghoul(telegram_id=600_000_001, health=10, max_health=10)

    row = _due_row(600_000_001, NotificationType.HEALTH_FULL)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert len(fake_bot.sent) == 1
    chat_id, text = fake_bot.sent[0]
    assert chat_id == 600_000_001
    assert "восстановил здоровье" in text


async def test_handle_due_skips_health_full_if_no_longer_true(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, make_user, make_ghoul,
):
    """Между постановкой пуша и тиком гуль мог потерять здоровье (бой) -
    отправлять устаревшее "здоровье полное" нельзя."""
    await make_user(telegram_id=600_000_002)
    await make_ghoul(telegram_id=600_000_002, health=1, max_health=10)

    row = _due_row(600_000_002, NotificationType.HEALTH_FULL)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert fake_bot.sent == []


async def test_handle_due_sends_hunger_threshold_message(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, make_user, make_ghoul,
):
    await make_user(telegram_id=600_000_003)
    await make_ghoul(telegram_id=600_000_003, hunger=70)

    row = _due_row(600_000_003, NotificationType.HUNGER_THRESHOLD, threshold=75)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert len(fake_bot.sent) == 1
    _, text = fake_bot.sent[0]
    assert "75" in text


async def test_handle_due_sends_hunger_zero_message(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, make_user, make_ghoul,
):
    """threshold=0 - настоящее (не заглушка) предупреждение: голод дошёл до
    0%, следующая же убыль убьёт. threshold=-1 - отдельный, тихий случай."""
    await make_user(telegram_id=600_000_004)
    await make_ghoul(telegram_id=600_000_004, hunger=0)

    row = _due_row(600_000_004, NotificationType.HUNGER_THRESHOLD, threshold=0)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert len(fake_bot.sent) == 1
    _, text = fake_bot.sent[0]
    assert "0%" in text


async def test_handle_due_silent_for_death_alarm_threshold(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, make_user, make_ghoul,
):
    """threshold=-1 - не настоящий процент, а будильник на момент
    потенциальной смерти - никакого текстового уведомления не шлёт сам по
    себе (реальная смерть, если наступила, обрабатывается materialize_passive_stats
    + отдельным DEATH-уведомлением)."""
    await make_user(telegram_id=600_000_006)
    await make_ghoul(telegram_id=600_000_006, hunger=0)

    row = _due_row(600_000_006, NotificationType.HUNGER_THRESHOLD, threshold=-1)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert fake_bot.sent == []


async def test_handle_due_skips_hunger_threshold_if_already_eaten(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, make_user, make_ghoul,
):
    await make_user(telegram_id=600_000_005)
    await make_ghoul(telegram_id=600_000_005, hunger=90)  # уже выше порога 75

    row = _due_row(600_000_005, NotificationType.HUNGER_THRESHOLD, threshold=75)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert fake_bot.sent == []


async def test_handle_due_cleans_up_missing_ghoul(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, session,
):
    row = _due_row(999_999_999, NotificationType.HEALTH_FULL)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert fake_bot.sent == []


async def test_handle_due_sends_death_notification_from_snapshot(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, make_user, make_ghoul,
):
    await make_user(telegram_id=600_000_007)
    await make_ghoul(telegram_id=600_000_007, level=5, lifetime_rc_earned=42, is_dead=True)
    await death_log_repository.insert(
        telegram_id=600_000_007, cause="starvation", level=5, lifetime_rc_earned=42
    )

    row = _due_row(600_000_007, NotificationType.DEATH)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert len(fake_bot.sent) == 1
    _, text = fake_bot.sent[0]
    assert "5" in text
    assert "42" in text
    assert "голода" in text


async def test_handle_due_skips_death_notification_if_already_reborn(
    ticker, fake_bot, ghoul_service, notification_repository, death_log_repository,
    fake_media_service, make_user, make_ghoul,
):
    """Гонка: гуль успел возродиться ("растить кагуне") раньше, чем тикер
    дошёл до DEATH-строки - некролог про уже неактуальную смерть не нужен."""
    await make_user(telegram_id=600_000_008)
    await make_ghoul(telegram_id=600_000_008, is_dead=False)
    await death_log_repository.insert(
        telegram_id=600_000_008, cause="starvation", level=3, lifetime_rc_earned=10
    )

    row = _due_row(600_000_008, NotificationType.DEATH)
    await _handle(ticker, row, ghoul_service, notification_repository, death_log_repository,
                  fake_media_service)

    assert fake_bot.sent == []
