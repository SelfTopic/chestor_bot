import html
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.dialogs import Dialogs, Line

from ...repositories import DueExpiration, ModerationRepository
from ...types import ModerationActionType, ModerationVoice
from ..dialog import DialogService
from ..notify import NotifyError, Notifier
from ..ticker import Ticker

logger = logging.getLogger(__name__)


class ModerationTicker(Ticker):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        notifier: Notifier,
        dialog_service: DialogService,
        interval_seconds: float = 30.0,
    ) -> None:
        super().__init__(interval_seconds)
        self._session_factory = session_factory
        self._notifier = notifier
        self._dialog_service = dialog_service

    async def tick(self) -> None:
        # Отметка ставится до отправки: недоставленное объявление теряется, но не шлётся
        # каждые 30 секунд заново.
        async with self._session_factory() as session:
            repository = ModerationRepository(session)
            due = await repository.due_expirations()
            await repository.mark_expirations_notified()
            await session.commit()

        for expiration in due:
            await self._announce(expiration)

    async def _announce(self, expiration: DueExpiration) -> None:
        phrases = (
            Dialogs.moderation.rough
            if expiration.voice is ModerationVoice.ROUGH
            else Dialogs.moderation.neutral
        )
        name = html.escape(expiration.first_name or str(expiration.target_id))
        mention = f'<a href="tg://user?id={expiration.target_id}">{name}</a>'
        who = dict(
            chat=html.escape(expiration.chat_title or str(expiration.chat_id)),
            name=name,
            id=expiration.target_id,
        )
        counts = dict(count=expiration.warns_left, limit=expiration.warn_limit)

        match expiration.kind:
            case ModerationActionType.MUTE:
                await self._send(expiration.chat_id, phrases.mute_expired(name=mention))
                log = phrases.log_mute_expired(**who)
            case ModerationActionType.BAN:
                log = phrases.log_ban_expired(**who)
            case _:
                await self._send(
                    expiration.chat_id, phrases.warn_expired(name=mention, **counts)
                )
                log = phrases.log_warn_expired(**who, **counts)

        if expiration.admin_chat_id is not None:
            await self._send(expiration.admin_chat_id, log)

    async def _send(self, chat_id: int, line: Line) -> None:
        try:
            await self._notifier.send_message(
                chat_id, self._dialog_service.text(line), parse_mode="HTML"
            )
        except NotifyError:
            logger.warning("Чат %s не получил объявление модерации", chat_id)
