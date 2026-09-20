from dataclasses import dataclass

from selfrot import BaseContext, TEvent
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.containers import Container
from src.bot.services import UserService
from src.bot.services.dialog import DialogService


@dataclass
class AppContext(BaseContext[TEvent]):
    """
    Контекст одного апдейта. Вместо Provide[Container...] у прода: сервисы берутся из
    контейнера, а сессия БД лежит в session_context (её кладёт DatabaseMiddleware).
    """

    dialog_service: DialogService
    container: Container
    session_factory: async_sessionmaker[AsyncSession]

    @property
    def user_service(self) -> UserService:
        # Собирается на каждое обращение и берёт сессию из session_context, как
        # Provide[Container.user_service]: работает после DatabaseMiddleware.
        return self.container.user_service()
