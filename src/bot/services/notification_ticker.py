import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.dialogs import Dialogs, Line
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
from src.bot.services.language import LanguageService
from src.bot.types import MediaDownloadType, NotificationType
from src.bot.utils import utcnow_naive
from src.database.models import DeathLog, ScheduledNotification

from .media_paths import random_media
from .notify import NotifyError, Notifier

logger = logging.getLogger(__name__)

_DEATH_CAUSES = {
    "starvation": Dialogs.notify.death_cause.starvation(),
    "eaten": Dialogs.notify.death_cause.eaten(),
    "admin": Dialogs.notify.death_cause.admin(),
}


class NotificationTicker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        notifier: Notifier,
        dialog_service: DialogService,
    ) -> None:
        self._session_factory = session_factory
        self._notifier = notifier
        self._dialog_service = dialog_service

    async def tick(self) -> None:
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

            languages = LanguageService(
                UserRepository(session), ChatRepository(session), self._dialog_service
            )
            for row in due:
                await self._handle_due(
                    row,
                    ghoul_service,
                    notification_repository,
                    death_log_repository,
                    media_repository,
                    languages,
                )

            await session.commit()

    async def _handle_due(
        self,
        row: ScheduledNotification,
        ghoul_service: GhoulService,
        notification_repository: ScheduledNotificationRepository,
        death_log_repository: DeathLogRepository,
        media_repository: MediaRepository,
        languages: LanguageService,
    ) -> None:
        # Запоминаем до ghoul_service.get(): он пересчитает и переставит расписание.
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
                await self._send(telegram_id, Dialogs.notify.health_full(), languages)
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
                return
            if ghoul.hunger > threshold:
                logger.info(
                    f"NotificationTicker: hunger_threshold={threshold} for {telegram_id} "
                    f"stale (hunger={ghoul.hunger}), skipping"
                )
                return
            await self._send(
                telegram_id, Dialogs.notify.hunger(threshold=threshold), languages
            )
            return

        if notification_type == NotificationType.DEATH:
            await notification_repository.delete(telegram_id, NotificationType.DEATH)

            if not ghoul.is_dead:
                logger.info(
                    f"NotificationTicker: {telegram_id} already reborn before DEATH "
                    f"row was handled, skipping obituary"
                )
                return

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
            await self._send_death(telegram_id, death, media_repository, languages)
            return

        logger.warning(f"Unknown notification_type: {notification_type}")

    async def _send(
        self, telegram_id: int, line: Line, languages: LanguageService
    ) -> None:
        text = await languages.text_for(telegram_id)
        try:
            await self._notifier.send_message(telegram_id, text(line))
            logger.info(f"NotificationTicker: sent '{line.key}' to {telegram_id}")
        except NotifyError:
            logger.warning(
                f"Failed to send notification '{line.key}' to {telegram_id}",
                exc_info=True,
            )

    async def _send_death(
        self,
        telegram_id: int,
        death: DeathLog,
        media_repository: MediaRepository,
        languages: LanguageService,
    ) -> None:
        obituary = Dialogs.notify.death(
            cause=_DEATH_CAUSES.get(death.cause, death.cause),
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
            await self._send(telegram_id, obituary, languages)
            return

        text = (await languages.text_for(telegram_id))(obituary)

        try:
            try:
                await self._notifier.send_video(
                    telegram_id, media.telegram_file_id or media.path, caption=text
                )
            except NotifyError:
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
