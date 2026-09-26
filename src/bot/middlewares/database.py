from contextvars import Token

from selfrot import BaseMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.containers import session_context

from ..context import AppContext


class DatabaseMiddleware(BaseMiddleware[AppContext]):
    """Одна сессия на апдейт: открывается здесь, коммитится после хендлера."""

    session: AsyncSession
    token: Token[AsyncSession]

    async def pre_handle(self) -> bool:
        self.session = self.ctx.session_factory()
        self.token = session_context.set(self.session)
        return True

    async def post_handle(self, exc: BaseException | None = None) -> None:
        try:
            if exc is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            session_context.reset(self.token)
            await self.session.close()
