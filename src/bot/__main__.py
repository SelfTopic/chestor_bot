import asyncio
import logging
import os
import sys

from ghoul_quiz import DEFAULT_BASE_URL as DEFAULT_QUIZ_URL
from selfrot import BaseDispatcher
from selfrot.middleware import LoggingMiddleware
from selfrot.types import Message, Update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.containers import Container
from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import (
    ChatNotFound,
    ChatTextLengthError,
    GhoulNotFound,
    MediaNotFound,
    QuizEmailMissing,
    QuizSessionMissing,
    UserNotFound,
)
from src.bot.services.dialog import DialogService
from src.config import settings
from src.database import session_factory as default_session_factory

from .bot import AppBot
from .context import AppContext
from .logs import setup_logging
from .middlewares import BanMiddleware, DatabaseMiddleware, SyncEntitiesMiddleware
from .routers import RootRouter
from .routers.ghoul_routers.duel import DuelTicker
from .services.notification_ticker import NotificationTicker
from .services.notify import NotifyError, SelfrotBotNotifier
from .services.quiz import QuizService
from .services.roast import LlmClient, RoastPrompts, RoastService

logger = logging.getLogger(__name__)

WEBHOOK_PORT = 8999
# Сообщение в Telegram — до 4096 символов, остальное место под текст фразы.
ERROR_LIMIT = 3500


def error_line(exc: Exception) -> Line:
    match exc:
        case UserNotFound(query=query):
            return Dialogs.errors.username_not_found(username=query)
        case ChatNotFound():
            return Dialogs.errors.chat_not_found()
        case GhoulNotFound():
            return Dialogs.errors.ghoul_not_found()
        case QuizEmailMissing():
            return Dialogs.errors.quiz.email_missing()
        case QuizSessionMissing(email=email):
            return Dialogs.errors.quiz.session_missing(email=email)
        case ChatTextLengthError(kind="rules"):
            return Dialogs.errors.chat_text_length.rules()
        case ChatTextLengthError(kind="welcome"):
            return Dialogs.errors.chat_text_length.welcome()
        case ChatTextLengthError(kind="goodbye"):
            return Dialogs.errors.chat_text_length.goodbye()
        case MediaNotFound():
            return Dialogs.errors.media_not_found()
        case _:
            return Dialogs.errors.unexpected(error=str(exc))


class Dispatcher(BaseDispatcher[AppContext]):
    bot = AppBot
    routers = (RootRouter,)
    context = AppContext
    # Порядок важен: первая middleware — внешняя.
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
        self.dialog_service = DialogService(on_broken=self.report_broken_texts)
        self.alerts: set[asyncio.Task[None]] = set()
        self.container = Container()
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
        api_key = settings.LLM_API_KEY.get_secret_value()
        self.llm = LlmClient(settings.LLM_BASE_URL, api_key)
        self.roast_service = RoastService(
            session_factory,
            self.llm,
            RoastPrompts(),
            enabled=settings.ROAST_ENABLED and bool(api_key),
            model=settings.ROAST_MODEL,
            classifier_model=settings.ROAST_CLASSIFIER_MODEL,
            daily_limit=settings.ROAST_DAILY_LIMIT,
            timeout=settings.ROAST_TIMEOUT,
        )
        self.duel_ticker = DuelTicker(
            session_factory=session_factory,
            bot=self.api,
            container=self.container,
            dialog_service=self.dialog_service,
        )

    def report_broken_texts(self, error: Exception) -> None:
        # Тексты перечитываются внутри синхронного text(), поэтому отправка — отдельной
        # задачей; ссылка на неё хранится, иначе сборщик мусора может её убить.
        line = Dialogs.admin.texts_broken(error=str(error)[:ERROR_LIMIT])
        task = asyncio.create_task(self.alert_admins(line))
        self.alerts.add(task)
        task.add_done_callback(self.alerts.discard)

    async def alert_admins(self, line: Line) -> None:
        notifier = SelfrotBotNotifier(self.api)
        text = self.dialog_service.text(line)
        for admin_id in settings.ADMIN_IDS:
            try:
                await notifier.send_message(admin_id, text)
            except NotifyError:
                logger.warning("Админ %s не получил сообщение от бота", admin_id)

    def create_context(self, update: Update) -> AppContext:
        return self.context(
            update,
            self.api,
            self.dialog_service,
            self.container,
            self.session_factory,
            self.quiz_service,
            self.roast_service,
        )

    async def on_startup(self) -> None:
        # Перед любым режимом старый вебхук снимается (иначе polling получит 409),
        # накопившиеся апдейты отбрасываются.
        await self.api.delete_webhook(drop_pending_updates=True)
        await self.container.video_worker().start()
        await self.notification_ticker.start()
        await self.duel_ticker.start()
        self.roast_service.bot_id = (await self.api.get_me()).id
        await self.roast_service.cleanup()

    async def on_shutdown(self) -> None:
        await self.container.video_worker().stop()
        await self.notification_ticker.stop()
        await self.duel_ticker.stop()
        await self.quiz_service.close()
        await self.llm.close()

    async def on_error(self, ctx: AppContext, exc: Exception) -> None:
        await super().on_error(ctx, exc)

        if isinstance(ctx.event, Message):
            await ctx.say(error_line(exc))


def main() -> None:
    try:
        setup_logging()
    except ValueError as e:
        sys.exit(str(e))

    token = settings.BOT_TOKEN.get_secret_value()

    # Секрет вебхука — в заголовке, а не в пути URL: путь попадает в логи nginx.
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
