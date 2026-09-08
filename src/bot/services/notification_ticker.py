import asyncio
import logging
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile

from src.database import session_factory
from src.database.models import ScheduledNotification

from ..repositories import (
    ChatRepository,
    DeathLogRepository,
    GhoulRepository,
    MediaRepository,
    ScheduledNotificationRepository,
    UserCooldownRepository,
    UserRepository,
)
from ..types import NotificationType
from ..utils import utcnow_naive
from .dialog import DialogService
from .ghoul import GhoulService
from .media import MediaDownloader, MediaService

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
        # MediaDownloader сам по себе не завязан на сессию БД (в отличие от
        # MediaRepository) - можно построить один раз, не пересоздавать
        # каждый тик.
        self._media_downloader = MediaDownloader(bot=bot)

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
                logger.debug(f"NotificationTicker tick at {now}: nothing due")
                return

            logger.info(f"NotificationTicker tick at {now}: {len(due)} due notification(s)")

            death_log_repository = DeathLogRepository(session)

            ghoul_service = GhoulService(
                UserRepository(session),
                GhoulRepository(session),
                UserCooldownRepository(session),
                ChatRepository(session),
                notification_repository,
                death_log_repository,
            )
            media_service = MediaService(
                downloader=self._media_downloader,
                media_repository=MediaRepository(session),
            )

            for row in due:
                await self._handle_due(
                    row, ghoul_service, notification_repository, death_log_repository,
                    media_service,
                )

            await session.commit()

    async def _handle_due(
        self,
        row: ScheduledNotification,
        ghoul_service: GhoulService,
        notification_repository: ScheduledNotificationRepository,
        death_log_repository: DeathLogRepository,
        media_service: MediaService,
    ) -> None:
        # Запоминаем, о чём была эта конкретная запись, ДО того как
        # ghoul_service.get() пересчитает и переставит расписание дальше.
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
                logger.warning(f"Death notification for {telegram_id} with no DeathLog row")
                return

            logger.info(
                f"NotificationTicker: sending obituary to {telegram_id} "
                f"(cause={death.cause}, level={death.level})"
            )
            await self._send_death(telegram_id, death, media_service)
            return

        logger.warning(f"Unknown notification_type: {notification_type}")

    async def _send(self, telegram_id: int, key: str, **kwargs) -> None:
        try:
            await self._bot.send_message(
                chat_id=telegram_id, text=self._dialog_service.text(key=key, **kwargs)
            )
            logger.info(f"NotificationTicker: sent '{key}' to {telegram_id}")
        except Exception:
            logger.warning(
                f"Failed to send notification '{key}' to {telegram_id}", exc_info=True
            )

    _DEATH_CAUSE_TEXT = {
        "starvation": "умер от голода",
        "eaten": "был съеден другим гулем",
        "admin": "был убит рукой создателя (/kill_ghoul)",
    }

    async def _send_death(self, telegram_id: int, death, media_service: MediaService) -> None:
        """Некролог - опенинг (если уже загружен через /add_gif death) +
        сводка по снапшоту DeathLog, не по живому (уже мёртвому/возможно
        сброшенному) гулю."""

        text = self._dialog_service.text(
            key="notify_death",
            cause=self._DEATH_CAUSE_TEXT.get(death.cause, death.cause),
            level=death.level,
            lifetime_rc_earned=death.lifetime_rc_earned,
        )

        media = None
        try:
            media = await media_service.get_random_video("death", user_id=telegram_id)
        except Exception:
            logger.warning("Failed to look up death video", exc_info=True)

        logger.info(
            f"NotificationTicker: death video for {telegram_id}: "
            f"{'found, ' + str(media.path) if media else 'none uploaded yet, text-only'}"
        )

        try:
            if not media:
                await self._bot.send_message(chat_id=telegram_id, text=text)
                logger.info(f"NotificationTicker: sent obituary (text-only) to {telegram_id}")
                return

            try:
                await self._bot.send_video(
                    chat_id=telegram_id,
                    video=media.telegram_file_id or FSInputFile(media.path),
                    caption=text,
                )
            except TelegramBadRequest:
                logger.info(
                    f"NotificationTicker: cached file_id for death video stale, "
                    f"re-uploading for {telegram_id}"
                )
                sent = await self._bot.send_video(
                    chat_id=telegram_id, video=FSInputFile(media.path), caption=text
                )
                if sent.video:
                    await media_service.update_telegram_file_id(
                        path=media.path, new_file_id=sent.video.file_id
                    )
            logger.info(f"NotificationTicker: sent obituary (with video) to {telegram_id}")
        except Exception:
            logger.warning(
                f"Failed to send death notification to {telegram_id}", exc_info=True
            )


__all__ = ["NotificationTicker"]
