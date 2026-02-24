import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from src.bot.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> None:
        user = None

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            await handler(event, data)
            return

        session = data.get("session")
        if not session:
            await handler(event, data)
            return

        repo = UserRepository(session)
        db_user = await repo.get(user.id)

        if db_user and db_user.is_banned:
            if db_user.banned_until and db_user.banned_until < datetime.now(
                timezone.utc
            ):
                await repo.unban(user.id)
                await handler(event, data)
                return

            reason = db_user.ban_reason or "причина не указана"
            until = (
                f"до {db_user.banned_until.strftime('%d.%m.%Y %H:%M')} UTC"
                if db_user.banned_until
                else "навсегда"
            )

            if isinstance(event, CallbackQuery):
                await event.answer(
                    f"🚫 Вы заблокированы ({until}). Причина: {reason}",
                    show_alert=True,
                )
            return

        await handler(event, data)
