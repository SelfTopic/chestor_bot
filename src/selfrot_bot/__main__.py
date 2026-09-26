import logging
import os
import sys

from dependency_injector import providers
from ghoul_quiz import DEFAULT_BASE_URL as DEFAULT_QUIZ_URL
from selfrot import BaseDispatcher
from selfrot.middleware import LoggingMiddleware
from selfrot.types import Message, Update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.containers import Container
from src.bot.services.dialog import DialogService
from src.config import settings
from src.database import session_factory as default_session_factory

from .bot import AppBot
from .context import AppContext
from .logs import setup_logging
from .media import UnsupportedMediaDownloader
from .middlewares import BanMiddleware, DatabaseMiddleware, SyncEntitiesMiddleware
from .routers import RootRouter
from .routers.ghoul_routers.duel import DuelTicker
from .services.notification_ticker import NotificationTicker
from .services.notify import SelfrotBotNotifier
from .services.quiz import QuizService

logger = logging.getLogger(__name__)

# Как у прода: nginx отдаёт https://chestor.site/webhook… на 127.0.0.1:8999.
WEBHOOK_PORT = 8999


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
        # Один клиент квиза на процесс: refresh-токены ghoul_quiz 0.2 одноразовые.
        self.quiz_service = QuizService(
            email=os.environ.get("GHOUL_QUIZ_EMAIL"),
            base_url=os.environ.get("GHOUL_QUIZ_API_URL", DEFAULT_QUIZ_URL),
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
            self.quiz_service,
        )

    async def on_startup(self) -> None:
        # Как у прода, перед любым режимом: старый вебхук снимается (иначе polling
        # получает 409), накопившиеся апдейты отбрасываются. В режиме вебхука
        # библиотека ставит новый уже после on_startup.
        await self.api.delete_webhook(drop_pending_updates=True)
        await self.container.video_worker().start()
        await self.notification_ticker.start()
        await self.duel_ticker.start()

    async def on_shutdown(self) -> None:
        await self.container.video_worker().stop()
        await self.notification_ticker.stop()
        await self.duel_ticker.stop()
        await self.quiz_service.close()

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
    try:
        setup_logging()
    except ValueError as e:
        sys.exit(str(e))

    # Порт и есть бот: токен — BOT_TOKEN, как у прода (обязателен в src.config).
    token = settings.BOT_TOKEN.get_secret_value()

    # Как у прода: ENV=DEV — polling, иначе вебхук. В отличие от прода секрет не в
    # пути URL (там токен бота попадал в логи nginx), а в заголовке, как требует
    # selfrotgram.
    dispatcher = Dispatcher(token=token)
    logger.info("ENV is %s", settings.ENV)
    if settings.ENV == "DEV":
        dispatcher.start_polling()
        return

    url = os.environ.get("WEBHOOK_URL")
    secret = os.environ.get("WEBHOOK_SECRET")
    if not url or not secret:
        sys.exit(
            f"ENV={settings.ENV} значит вебхук: задайте WEBHOOK_URL "
            "и WEBHOOK_SECRET (или ENV=DEV для polling)"
        )
    dispatcher.start_webhook(
        url=url, secret_token=secret, host="0.0.0.0", port=WEBHOOK_PORT
    )


if __name__ == "__main__":
    main()
