import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from dependency_injector.wiring import Provide

from src.bot.containers import Container
from src.bot.services import UserService

logger = logging.getLogger(__name__)


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
        user_service: UserService = Provide[Container.user_service],
    ) -> None:
        logger.debug("BanMiddleware called for event: %s", type(event).__name__)
        user = None

        if isinstance(event, Update):
            if event.message and event.message.from_user:
                user = event.message.from_user
            elif event.callback_query and event.callback_query.from_user:
                user = event.callback_query.from_user

            if not isinstance(event.event, Message) and not isinstance(
                event.event, CallbackQuery
            ):
                logger.warning("Unsupported event type for BanMiddleware")
                await handler(event, data)
                return
            user = (
                event.message.from_user
                if event.message
                else event.callback_query.from_user
                if event.callback_query
                else None
            )

        else:
            logger.warning("Event is not an Update, skipping BanMiddleware")
            await handler(event, data)
            return

        if not user:
            await handler(event, data)
            return

        db_user = await user_service.get(user.id)

        if db_user and db_user.is_banned:
            if db_user.banned_until and db_user.banned_until < datetime.now(
                timezone.utc
            ):
                await user_service.user_repository.unban(user.id)
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

            logger.info(
                "User %s is banned until %s. Reason: %s", user.id, until, reason
            )
            return

        logger.debug("User %s is not banned, proceeding with handler", user.id)
        await handler(event, data)
