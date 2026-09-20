import logging
import os
import sys

from selfrot import BaseDispatcher
from selfrot.middleware import LoggingMiddleware
from selfrot.types import Update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.containers import Container
from src.bot.services.dialog import DialogService
from src.database import session_factory as default_session_factory

from .context import AppContext
from .middlewares import BanMiddleware, DatabaseMiddleware, SyncEntitiesMiddleware
from .routers import RootRouter


class Dispatcher(BaseDispatcher[AppContext]):
    routers = (RootRouter,)
    context = AppContext
    # Как dp.update.middleware у прода: первая снаружи. Logging → Database → Sync → Ban.
    middlewares = (
        LoggingMiddleware,
        DatabaseMiddleware,
        SyncEntitiesMiddleware,
        BanMiddleware,
    )

    def __init__(
        self,
        token: str | None = None,
        session_factory: async_sessionmaker[AsyncSession] = default_session_factory,
    ) -> None:
        super().__init__(token)
        self.dialog_service = DialogService()
        # Контейнер без bot: сервисы, которым нужен aiogram Bot (MediaDownloader,
        # BroadcastService, NotificationTicker, LevelUpService), пока не переносятся.
        self.container = Container()
        self.session_factory = session_factory

    def create_context(self, update: Update) -> AppContext:
        return self.context(
            update,
            self.api,
            self.dialog_service,
            self.container,
            self.session_factory,
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    # Отдельная переменная, а не BOT_TOKEN из .env: порт нельзя случайно запустить
    # на токене прод-бота.
    token = os.environ.get("SELFROT_BOT_TOKEN")
    if not token:
        sys.exit("Задайте SELFROT_BOT_TOKEN (токен dev-бота, не прод)")

    Dispatcher(token=token).start_polling()


if __name__ == "__main__":
    main()
