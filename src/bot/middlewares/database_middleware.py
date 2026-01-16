import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..containers import session_context

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware for connect database"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            token = session_context.set(session)

            try:
                await handler(event, data)
                logger.debug("Processed handler of database session")
                await session.commit()
                logger.debug("Database session commited")

            except Exception as e:
                logger.exception(f"Error processed handler of database session: {e}")
                await session.rollback()
                raise

            finally:
                session_context.reset(token)


__all__ = ["DatabaseMiddleware"]
