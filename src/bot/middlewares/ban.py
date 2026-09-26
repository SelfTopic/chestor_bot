import logging
from datetime import datetime, timezone

from selfrot import BaseMiddleware
from selfrot.types import CallbackQuery, Message

from ..context import AppContext

logger = logging.getLogger(__name__)


class BanMiddleware(BaseMiddleware[AppContext]):
    async def pre_handle(self) -> bool:
        event = self.ctx.event
        if not isinstance(event, (Message, CallbackQuery)) or event.user is None:
            return True

        user_service = self.ctx.user_service
        db_user = await user_service.get(event.user.id)
        if db_user is None or not db_user.is_banned:
            return True

        # Колонка без часового пояса: из БД приходит наивное время, считаем его UTC, иначе
        # сравнение с aware падает с TypeError.
        banned_until = db_user.banned_until
        if banned_until is not None and banned_until.tzinfo is None:
            banned_until = banned_until.replace(tzinfo=timezone.utc)

        if banned_until and banned_until < datetime.now(timezone.utc):
            await user_service.user_repository.unban(event.user.id)
            return True

        reason = db_user.ban_reason or "причина не указана"
        until = (
            f"до {banned_until.strftime('%d.%m.%Y %H:%M')} UTC"
            if banned_until
            else "навсегда"
        )

        if isinstance(event, CallbackQuery):
            await event.answer(
                f"🚫 Вы заблокированы ({until}). Причина: {reason}", show_alert=True
            )

        logger.info(
            "User %s is banned until %s. Reason: %s", event.user.id, until, reason
        )
        return False

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
