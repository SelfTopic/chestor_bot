import asyncio
import logging
from typing import Optional

from aiogram import Bot

from src.database import session_factory
from src.database.models import ScheduledNotification

from ..repositories import (
    ChatRepository,
    GhoulRepository,
    ScheduledNotificationRepository,
    UserCooldownRepository,
    UserRepository,
)
from ..types import NotificationType
from ..utils import utcnow_naive
from .dialog import DialogService
from .ghoul import GhoulService

logger = logging.getLogger(__name__)


class NotificationTicker:
    """Лёгкий фоновый тикер под scheduled_notifications, см.
    BATTLE_DESIGN.md ("Механизм regen/hunger"). Читает только эту таблицу
    (не сканирует всех гулей), поэтому может себе позволить редкий интервал.

    Единственное осознанное исключение из правила "фон не мутирует БД" -
    сам пересчёт расписания (через GhoulService.get -> materialize_passive_stats)
    попутно материализует голод/хп гуля, который иначе никто бы не прочитал."""

    def __init__(
        self,
        bot: Bot,
        dialog_service: DialogService,
        interval_seconds: float = 30.0,
    ) -> None:
        self._bot = bot
        self._dialog_service = dialog_service
        self._interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            logger.warning("NotificationTicker is already running")
            return

        logger.info(f"Starting NotificationTicker (interval={self._interval}s)")
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if not self._running:
            return

        logger.info("Stopping NotificationTicker...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("NotificationTicker stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.error("NotificationTicker tick failed", exc_info=True)

            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

    async def _tick(self) -> None:
        now = utcnow_naive()

        async with session_factory() as session:
            notification_repository = ScheduledNotificationRepository(session)
            due = await notification_repository.get_due(now)

            if not due:
                return

            logger.debug(f"NotificationTicker: {len(due)} due notification(s)")

            ghoul_service = GhoulService(
                UserRepository(session),
                GhoulRepository(session),
                UserCooldownRepository(session),
                ChatRepository(session),
                notification_repository,
            )

            for row in due:
                await self._handle_due(row, ghoul_service, notification_repository)

            await session.commit()

    async def _handle_due(
        self,
        row: ScheduledNotification,
        ghoul_service: GhoulService,
        notification_repository: ScheduledNotificationRepository,
    ) -> None:
        # Запоминаем, о чём была эта конкретная запись, ДО того как
        # ghoul_service.get() пересчитает и переставит расписание дальше.
        notification_type = row.notification_type
        threshold = row.threshold
        telegram_id = row.telegram_id

        ghoul = await ghoul_service.get(telegram_id)

        if not ghoul:
            logger.warning(
                f"Scheduled notification for missing ghoul {telegram_id}, dropping"
            )
            await notification_repository.delete(telegram_id, notification_type)
            return

        if notification_type == NotificationType.HEALTH_FULL:
            if ghoul.health >= ghoul.max_health:
                await self._send(telegram_id, key="notify_health_full")
            return

        if notification_type == NotificationType.HUNGER_THRESHOLD:
            if threshold is None or ghoul.hunger > threshold:
                return  # состояние уже успело измениться - расписание само поправлено

            if threshold == 0:
                await self._send(telegram_id, key="notify_hunger_zero")
            else:
                await self._send(
                    telegram_id, key="notify_hunger_threshold", threshold=threshold
                )
            return

        logger.warning(f"Unknown notification_type: {notification_type}")

    async def _send(self, telegram_id: int, key: str, **kwargs) -> None:
        try:
            await self._bot.send_message(
                chat_id=telegram_id, text=self._dialog_service.text(key=key, **kwargs)
            )
        except Exception:
            logger.warning(
                f"Failed to send notification '{key}' to {telegram_id}", exc_info=True
            )


__all__ = ["NotificationTicker"]
