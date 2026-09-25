import logging
import os
import sys

from dependency_injector import providers
from selfrot import BaseDispatcher
from selfrot.middleware import LoggingMiddleware
from selfrot.types import Message, Update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.containers import Container
from src.bot.services.dialog import DialogService
from src.database import session_factory as default_session_factory

from .bot import AppBot
from .context import AppContext
from .media import UnsupportedMediaDownloader
from .middlewares import BanMiddleware, DatabaseMiddleware, SyncEntitiesMiddleware
from .routers import RootRouter
from .routers.ghoul_routers.duel import DuelTicker
from .services.notification_ticker import NotificationTicker
from .services.notify import SelfrotBotNotifier

logger = logging.getLogger(__name__)


class Dispatcher(BaseDispatcher[AppContext]):
    bot = AppBot
    routers = (RootRouter,)
    context = AppContext
    # Как dp.update.middleware у прода: первая снаружи. Logging → Database → Sync → Ban.
    middlewares = (
        LoggingMiddleware,
        DatabaseMiddleware,
        SyncEntitiesMiddleware,
        BanMiddleware,
    )
    handlers = ()

    def __init__(
        self,
        token: str | None = None,
        session_factory: async_sessionmaker[AsyncSession] = default_session_factory,
    ) -> None:
        super().__init__(token)
        self.dialog_service = DialogService()
        # Контейнер без bot: сервисы, которым нужен aiogram Bot (BroadcastService,
        # LevelUpService, старый NotificationTicker), в него больше не ходят — у порта
        # свои версии в .services, на Notifier вместо aiogram Bot (см. context.py и
        # notification_ticker ниже). MediaDownloader (bot.download) заменён заглушкой:
        # старому MediaService он ещё нужен как параметр конструктора, хотя /add_gif
        # (единственный, кто раньше был вызывающим) теперь качает через ctx.download.
        self.container = Container()
        self.container.media_downloader.override(
            providers.Factory(UnsupportedMediaDownloader)
        )
        self.session_factory = session_factory
        self.notification_ticker = NotificationTicker(
            session_factory=session_factory,
            notifier=SelfrotBotNotifier(self.api),
            dialog_service=self.dialog_service,
        )
        self.duel_ticker = DuelTicker(
            session_factory=session_factory,
            bot=self.api,
            container=self.container,
            dialog_service=self.dialog_service,
        )

    def create_context(self, update: Update) -> AppContext:
        return self.context(
            update,
            self.api,
            self.dialog_service,
            self.container,
            self.session_factory,
        )

    async def on_startup(self) -> None:
        await self.container.video_worker().start()
        await self.notification_ticker.start()
        await self.duel_ticker.start()

    async def on_shutdown(self) -> None:
        await self.container.video_worker().stop()
        await self.notification_ticker.stop()
        await self.duel_ticker.stop()

    async def on_error(self, ctx: AppContext, exc: Exception) -> None:
        """
        Замена error_router прода: ошибку в лог, а если апдейт был сообщением, то
        ответить текстом global_error. Показывать пользователю str(exc) любого
        исключения небезопасно (уйдут детали БД), но так делает и прод.
        """
        await super().on_error(ctx, exc)

        event = ctx.event
        if isinstance(event, Message):
            await event.answer(
                self.dialog_service.text(key="global_error", error=str(exc))
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
