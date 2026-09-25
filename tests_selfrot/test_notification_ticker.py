"""
NotificationTicker: конструируется напрямую (без Dispatcher — это фоновый объект, а
не часть маршрутизации апдейтов), проверяется FakeNotifier'ом. Один тест (кешированный
file_id для видео) идёт через настоящий SelfrotBotNotifier поверх фейкового Telegram —
чтобы убедиться, что адаптер собирает send_video правильно, а не просто что тикер его
вызвал.
"""

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from src.bot.repositories import GhoulRepository, MediaRepository
from src.bot.services.dialog import DialogService
from src.bot.types import NotificationType
from src.bot.utils import utcnow_naive
from src.database.models import DeathLog, Media, ScheduledNotification
from src.selfrot_bot.services.notification_ticker import NotificationTicker
from src.selfrot_bot.services.notify import NotifyError, SelfrotBotNotifier

from .test_common_routers import seed

UID = 700030  # > 666000: GhoulService.get() считает такие telegram_id, а не id гуля


class FakeNotifier:
    def __init__(self, fail_video_for: frozenset[str] = frozenset()):
        self.messages: list[tuple[int, str]] = []
        self.videos: list[tuple[int, str]] = []
        self.fail_video_for = fail_video_for

    async def send_message(self, chat_id, text, *, parse_mode=None):
        self.messages.append((chat_id, text))

    async def send_video(self, chat_id, video, *, caption=None):
        if video in self.fail_video_for:
            raise NotifyError("устаревший file_id")
        self.videos.append((chat_id, str(video)))
        return "NEW_FILE_ID"


@pytest.fixture
def dialog_service() -> DialogService:
    return DialogService()


@pytest.fixture
def ticker(session_factory, dialog_service) -> tuple[NotificationTicker, FakeNotifier]:
    notifier = FakeNotifier()
    return NotificationTicker(session_factory, notifier, dialog_service), notifier


async def seed_ghoul(session_factory, telegram_id: int, **fields):
    await seed(session_factory, telegram_id, "Вася")
    async with session_factory() as session:
        await GhoulRepository(session).upsert(telegram_id=telegram_id, **fields)
        await session.commit()


async def seed_due(
    session_factory,
    telegram_id: int,
    notification_type: NotificationType,
    threshold: int | None = None,
) -> None:
    async with session_factory() as session:
        session.add(
            ScheduledNotification(
                telegram_id=telegram_id,
                notification_type=notification_type.value,
                threshold=threshold,
                fire_at=utcnow_naive() - timedelta(seconds=1),
            )
        )
        await session.commit()


class TestHealthFull:
    async def test_sends_when_health_is_full(self, session_factory, ticker):
        notification_ticker, notifier = ticker
        await seed_ghoul(session_factory, UID, health=100, max_health=100)
        await seed_due(session_factory, UID, NotificationType.HEALTH_FULL)

        await notification_ticker._tick()

        (message,) = notifier.messages
        assert message[0] == UID

    async def test_skips_when_stale(self, session_factory, ticker):
        notification_ticker, notifier = ticker
        await seed_ghoul(session_factory, UID, health=50, max_health=100)
        await seed_due(session_factory, UID, NotificationType.HEALTH_FULL)

        await notification_ticker._tick()

        assert notifier.messages == []


class TestHungerThreshold:
    async def test_sends_when_reached(self, session_factory, ticker):
        # хендлер шлёт, когда голод УЖЕ опустился до порога или ниже (hunger <= threshold)
        notification_ticker, notifier = ticker
        await seed_ghoul(session_factory, UID, hunger=70)
        await seed_due(
            session_factory, UID, NotificationType.HUNGER_THRESHOLD, threshold=75
        )

        await notification_ticker._tick()

        assert len(notifier.messages) == 1

    async def test_skips_when_stale(self, session_factory, ticker):
        # к моменту тика голод успел вырасти обратно выше порога — расписание устарело
        notification_ticker, notifier = ticker
        await seed_ghoul(session_factory, UID, hunger=90)
        await seed_due(
            session_factory, UID, NotificationType.HUNGER_THRESHOLD, threshold=75
        )

        await notification_ticker._tick()

        assert notifier.messages == []

    async def test_death_alarm_marker_sends_nothing(self, session_factory, ticker):
        # threshold=-1 - не текстовое уведомление, "будильник" на потенциальную смерть
        notification_ticker, notifier = ticker
        await seed_ghoul(session_factory, UID, hunger=100, is_dead=True)
        await seed_due(
            session_factory, UID, NotificationType.HUNGER_THRESHOLD, threshold=-1
        )

        await notification_ticker._tick()

        assert notifier.messages == []


class TestDeath:
    # random_media (media_paths.py) находит файл, СКАНИРУЯ эту папку на диске — запись
    # в Media одной БД недостаточно, файл должен реально там лежать.
    VIDEO_FOLDER = Path("src/assets/video/death")

    async def seed_death(
        self, session_factory, telegram_id: int, cause: str = "starvation"
    ):
        async with session_factory() as session:
            session.add(
                DeathLog(
                    telegram_id=telegram_id,
                    cause=cause,
                    level=5,
                    lifetime_rc_earned=100,
                )
            )
            await session.commit()

    @pytest.fixture
    def video_file(self):
        """Единственный файл в папке коллекции на время теста (random_media берёт
        случайный из всех, что там лежат — с посторонними файлами тест был бы летучим)."""
        self.VIDEO_FOLDER.mkdir(parents=True, exist_ok=True)
        stray = list(self.VIDEO_FOLDER.iterdir())
        assert not stray, f"посторонние файлы в {self.VIDEO_FOLDER}: {stray}"

        path = self.VIDEO_FOLDER / "obituary.mp4"
        path.write_bytes(b"video")
        yield path
        path.unlink(missing_ok=True)

    async def test_missing_ghoul_drops_notification(self, session_factory, ticker):
        notification_ticker, notifier = ticker
        await seed(session_factory, UID, "Вася")  # пользователь есть, гуля - нет
        await seed_due(session_factory, UID, NotificationType.DEATH)

        await notification_ticker._tick()

        assert notifier.messages == notifier.videos == []

        # запись должна быть убрана, иначе тикер бесконечно спотыкался бы о неё
        async with session_factory() as session:
            row = await session.scalar(
                select(ScheduledNotification).where(
                    ScheduledNotification.telegram_id == UID
                )
            )
        assert row is None

    async def test_reborn_before_handled_skips_obituary(self, session_factory, ticker):
        notification_ticker, notifier = ticker
        await seed_ghoul(session_factory, UID, is_dead=False)  # успел возродиться
        await seed_due(session_factory, UID, NotificationType.DEATH)

        await notification_ticker._tick()

        assert notifier.messages == [] and notifier.videos == []

    async def test_text_only_without_media(self, session_factory, ticker):
        notification_ticker, notifier = ticker
        await seed_ghoul(session_factory, UID, is_dead=True)
        await self.seed_death(session_factory, UID)
        await seed_due(session_factory, UID, NotificationType.DEATH)

        await notification_ticker._tick()

        assert len(notifier.messages) == 1
        assert notifier.videos == []

    async def test_sends_video_with_cached_file_id(
        self, session_factory, dialog_service, video_file
    ):
        await seed_ghoul(session_factory, UID, is_dead=True)
        await self.seed_death(session_factory, UID)
        await seed_due(session_factory, UID, NotificationType.DEATH)

        async with session_factory() as session:
            session.add(
                Media(
                    media_type="video",
                    telegram_file_id="CACHED_ID",
                    collection="death:video",
                    path=str(video_file),
                    uploaded_by=UID,
                )
            )
            await session.commit()

        notifier = FakeNotifier()
        notification_ticker = NotificationTicker(
            session_factory, notifier, dialog_service
        )

        await notification_ticker._tick()

        assert notifier.videos == [(UID, "CACHED_ID")]

    async def test_stale_file_id_reuploads_and_updates_cache(
        self, session_factory, dialog_service, video_file
    ):
        await seed_ghoul(session_factory, UID, is_dead=True)
        await self.seed_death(session_factory, UID)
        await seed_due(session_factory, UID, NotificationType.DEATH)

        async with session_factory() as session:
            session.add(
                Media(
                    media_type="video",
                    telegram_file_id="STALE_ID",
                    collection="death:video",
                    path=str(video_file),
                    uploaded_by=UID,
                )
            )
            await session.commit()

        notifier = FakeNotifier(fail_video_for=frozenset({"STALE_ID"}))
        notification_ticker = NotificationTicker(
            session_factory, notifier, dialog_service
        )

        await notification_ticker._tick()

        assert notifier.videos == [(UID, str(video_file))]
        async with session_factory() as session:
            media = await MediaRepository(session).get_by_path(str(video_file))
        assert media is not None and media.telegram_file_id == "NEW_FILE_ID"


class TestSelfrotBotNotifierVideo:
    """Проверяет сам адаптер (не тикер): send_video собирает запрос правильно —
    file_id уходит строкой как есть, путь — файлом с диска."""

    async def test_file_id_is_sent_as_is(self, telegram, dispatcher):
        notifier = SelfrotBotNotifier(dispatcher.api)
        telegram.results["sendVideo"] = {
            "message_id": 1,
            "date": 5,
            "chat": {"id": UID, "type": "private"},
            "video": {
                "file_id": "CACHED_ID",
                "file_unique_id": "u",
                "width": 1,
                "height": 1,
                "duration": 1,
            },
        }

        file_id = await notifier.send_video(UID, "CACHED_ID", caption="некролог")

        (body,) = telegram.bodies("sendVideo")
        assert body["video"] == "CACHED_ID"
        assert file_id == "CACHED_ID"


class TestLifecycle:
    async def test_start_and_stop(self, session_factory, ticker):
        notification_ticker, _ = ticker

        await notification_ticker.start()
        assert notification_ticker._running

        await notification_ticker.stop()
        assert not notification_ticker._running
