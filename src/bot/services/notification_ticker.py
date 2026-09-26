"""
Фоновый тикер под scheduled_notifications: та же логика, что у прод-NotificationTicker
(тег aiogram-final). Отправка — через Notifier, поиск некролог-видео — через
media_paths.random_media.
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.repositories import (
    ChatRepository,
    DeathLogRepository,
    GhoulRepository,
    MediaRepository,
    ScheduledNotificationRepository,
    UserCooldownRepository,
    UserRepository,
)
from src.bot.services.dialog import DialogService
from src.bot.services.ghoul import GhoulService
from src.bot.types import MediaDownloadType, NotificationType
from src.bot.utils import utcnow_naive
from src.database.models import DeathLog, ScheduledNotification

from .media_paths import random_media
from .notify import NotifyError, Notifier

logger = logging.getLogger(__name__)

_DEATH_CAUSE_TEXT = {
    "starvation": "умер от голода",
    "eaten": "был съеден другим гулем",
    "admin": "был убит рукой создателя (/kill_ghoul)",
}


class NotificationTicker:
    """Лёгкий фоновый тикер под scheduled_notifications, см. BATTLE_DESIGN.md
    ("Механизм regen/hunger"). Читает только эту таблицу (не сканирует всех гулей),
    поэтому может себе позволить редкий интервал."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        notifier: Notifier,
        dialog_service: DialogService,
        interval_seconds: float = 30.0,
    ) -> None:
        self._session_factory = session_factory
        self._notifier = notifier
        self._dialog_service = dialog_service
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None
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

        async with self._session_factory() as session:
            notification_repository = ScheduledNotificationRepository(session)
            due = await notification_repository.get_due(now)

            if not due:
                logger.debug(f"NotificationTicker tick at {now}: nothing due")
                return

            logger.info(
                f"NotificationTicker tick at {now}: {len(due)} due notification(s)"
            )

            death_log_repository = DeathLogRepository(session)
            media_repository = MediaRepository(session)

            ghoul_service = GhoulService(
                UserRepository(session),
                GhoulRepository(session),
                UserCooldownRepository(session),
                ChatRepository(session),
                notification_repository,
                death_log_repository,
            )

            for row in due:
                await self._handle_due(
                    row,
                    ghoul_service,
                    notification_repository,
                    death_log_repository,
                    media_repository,
                )

            await session.commit()

    async def _handle_due(
        self,
        row: ScheduledNotification,
        ghoul_service: GhoulService,
        notification_repository: ScheduledNotificationRepository,
        death_log_repository: DeathLogRepository,
        media_repository: MediaRepository,
    ) -> None:
        # Запоминаем, о чём была эта конкретная запись, ДО того как ghoul_service.get()
        # пересчитает и переставит расписание дальше.
        notification_type = row.notification_type
        threshold = row.threshold
        telegram_id = row.telegram_id

        logger.info(
            f"NotificationTicker: handling {notification_type} for {telegram_id} "
            f"(threshold={threshold})"
        )

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
            else:
                logger.info(
                    f"NotificationTicker: health_full for {telegram_id} stale "
                    f"(health={ghoul.health}/{ghoul.max_health}), skipping"
                )
            return

        if notification_type == NotificationType.HUNGER_THRESHOLD:
            if threshold is None or threshold == -1:
                logger.debug(
                    f"NotificationTicker: {telegram_id} hunger death-alarm fired "
                    f"(hunger={ghoul.hunger}, is_dead={ghoul.is_dead}) - no text, "
                    f"materialize already handled it above if it was time"
                )
                return  # "будильник" смерти - не текстовое уведомление, см. выше
            if ghoul.hunger > threshold:
                logger.info(
                    f"NotificationTicker: hunger_threshold={threshold} for {telegram_id} "
                    f"stale (hunger={ghoul.hunger}), skipping"
                )
                return  # состояние уже успело измениться - расписание само поправилось
            await self._send(
                telegram_id, key="notify_hunger_threshold", threshold=threshold
            )
            return

        if notification_type == NotificationType.DEATH:
            await notification_repository.delete(telegram_id, NotificationType.DEATH)

            if not ghoul.is_dead:
                logger.info(
                    f"NotificationTicker: {telegram_id} already reborn before DEATH "
                    f"row was handled, skipping obituary"
                )
                return  # успел возродиться раньше, чем дошла очередь - некролог не нужен

            death = await death_log_repository.get_latest(telegram_id)
            if not death:
                logger.warning(
                    f"Death notification for {telegram_id} with no DeathLog row"
                )
                return

            logger.info(
                f"NotificationTicker: sending obituary to {telegram_id} "
                f"(cause={death.cause}, level={death.level})"
            )
            await self._send_death(telegram_id, death, media_repository)
            return

        logger.warning(f"Unknown notification_type: {notification_type}")

    async def _send(self, telegram_id: int, key: str, **kwargs: Any) -> None:
        try:
            await self._notifier.send_message(
                telegram_id, self._dialog_text(key, **kwargs)
            )
            logger.info(f"NotificationTicker: sent '{key}' to {telegram_id}")
        except NotifyError:
            logger.warning(
                f"Failed to send notification '{key}' to {telegram_id}", exc_info=True
            )

    def _dialog_text(self, key: str, **kwargs: Any) -> str:
        return self._dialog_service.text(key=key, **kwargs)

    async def _send_death(
        self, telegram_id: int, death: DeathLog, media_repository: MediaRepository
    ) -> None:
        """Некролог - опенинг (если уже загружен через /add_gif death) + сводка по
        снапшоту DeathLog, не по живому (уже мёртвому/возможно сброшенному) гулю."""

        text = self._dialog_text(
            "notify_death",
            cause=_DEATH_CAUSE_TEXT.get(death.cause, death.cause),
            level=death.level,
            lifetime_rc_earned=death.lifetime_rc_earned,
        )

        media = None
        try:
            media = await random_media(
                media_repository, MediaDownloadType.VIDEO, "death", telegram_id
            )
        except Exception:
            logger.warning("Failed to look up death video", exc_info=True)

        logger.info(
            f"NotificationTicker: death video for {telegram_id}: "
            f"{'found, ' + str(media.path) if media else 'none uploaded yet, text-only'}"
        )

        if not media:
            await self._send(telegram_id, "notify_death")
            return

        try:
            # Как у прода: если file_id ещё нет, первая отправка идёт файлом с диска, а
            # её собственный новый file_id не кешируется — кеш заполняется только через
            # ветку ниже (устаревший id). Сохранено как есть, не улучшение с моей стороны.
            try:
                await self._notifier.send_video(
                    telegram_id, media.telegram_file_id or media.path, caption=text
                )
            except NotifyError:
                # Кешированный file_id устарел (например, файл удалили из Telegram) -
                # перезаливаем с диска и запоминаем новый id на следующий раз.
                logger.info(
                    f"NotificationTicker: cached file_id for death video stale, "
                    f"re-uploading for {telegram_id}"
                )
                new_file_id = await self._notifier.send_video(
                    telegram_id, media.path, caption=text
                )
                await media_repository.update_file_id(
                    path=media.path, new_file_id=new_file_id
                )
            logger.info(
                f"NotificationTicker: sent obituary (with video) to {telegram_id}"
            )
        except NotifyError:
            logger.warning(
                f"Failed to send death notification to {telegram_id}", exc_info=True
            )
