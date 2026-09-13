import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories import (
    ChatRepository,
    GhoulRepository,
    UserCooldownRepository,
    UserRepository,
)
from ..services import SyncEntitiesService

logger = logging.getLogger(__name__)


class SyncEntitiesMiddleware(BaseMiddleware):
    """Апсертит User/Chat на КАЖДОЕ сообщение - намеренно в СВОЕЙ, сразу
    коммитящейся сессии, а не в общей сессии хендлера (`DatabaseMiddleware`
    открывает её раньше в цепочке и коммитит только после ВСЕГО хендлера).

    Раньше `sync()` работал через DI (`Provide[Container.sync_entities_
    service]`), который резолвится в ТУ ЖЕ ambient-сессию (`db_session =
    providers.Factory(lambda: session_context.get())` в containers.py) -
    из-за этого `INSERT ... ON CONFLICT DO UPDATE` на строку `User` держал
    строку залоченной до конца ВСЕГО хендлера, включая любую медленную,
    никак не связанную работу (например нарезку видео в anime_router,
    десятки секунд). Следующее сообщение от ТОГО ЖЕ пользователя (снова
    апсерт той же строки) реально ждало на уровне Postgres, пока не
    закоммитится первая транзакция - выглядело как "бот встал", хотя
    event loop был свободен. Тот же паттерн, что уже применяется в фоновых
    задачах (`duel/background.py`) - своя сессия через `session_factory`,
    не переиспользование сессии текущего хендлера."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> None:
        logger.debug("Calling sync entities")

        async with self.session_factory() as session:
            sync_service = SyncEntitiesService(
                user_repository=UserRepository(session),
                ghoul_repository=GhoulRepository(session),
                user_cooldown_repository=UserCooldownRepository(session),
                chat_repository=ChatRepository(session),
            )
            await sync_service.sync(event=event, bot=data["bot"])
            await session.commit()

        await handler(event, data)


__all__ = ["SyncEntitiesMiddleware"]
