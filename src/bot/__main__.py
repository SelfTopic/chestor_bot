import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from ghoul_quiz import DEFAULT_BASE_URL as DEFAULT_QUIZ_URL
from selfrot import BaseDispatcher
from selfrot.handlers import BaseHandler
from selfrot.middleware import LoggingMiddleware
from selfrot.types import Message, Update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import (
    ChatNotFound,
    ChatTextLengthError,
    GhoulNotFound,
    MediaNotFound,
    QuizBusy,
    QuizEmailMissing,
    QuizSessionMissing,
    UserNotFound,
)
from src.bot.services import (
    MobService,
    RpCommandsService,
    VideoCutterService,
    VideoWorker,
    WikipediaService,
    WordleService,
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
from .session_services import rp_commands_repository
from .services.moderation import ModerationTicker
from .services.notification_ticker import NotificationTicker
from .services.notify import NotifyError, SelfrotBotNotifier
from .services.quiz import QuizService
from .services.llm import LlmClient
from .services.analytics import AnalyticsRecorder, AnalyticsTicker
from .services.notify import TelegramDocsChannel
from .services.player_docs import PlayerDocsService
from .services.link_media import Downloader, LinkMediaService
from .services.media_tools import MediaToolsUpdater
from .services.music import MusicFinder, MusicService, Recognizer
from .services.roast import RoastPrompts, RoastService
from .services.search import SearchService, TavilyClient

logger = logging.getLogger(__name__)

WEBHOOK_PORT = 8999
# Сообщение в Telegram — до 4096 символов, остальное место под текст фразы.
ERROR_LIMIT = 3500
# Bot API принимает от бота файлы до 50 МБ; запас — на служебные поля multipart.
UPLOAD_LIMIT = 49 * 1024 * 1024


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
        case QuizBusy(retry_after=seconds):
            return Dialogs.errors.quiz.busy(seconds=seconds)
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
        self.session_factory = session_factory
        self.analytics = AnalyticsRecorder(session_factory)
        self.analytics_ticker = AnalyticsTicker(self.analytics)
        self.player_docs = PlayerDocsService(session_factory, Path(settings.DOCS_DIR))
        # Живут весь процесс: кэши RP-команд, партии вордли, очередь нарезки видео.
        self.rp_commands_service = RpCommandsService(rp_commands_repository)
        self.wordle_service = WordleService()
        self.wikipedia_service = WikipediaService()
        self.mob_service = MobService()
        self.video_cutter_service = VideoCutterService()
        self.video_worker = VideoWorker(self.video_cutter_service)
        self.notification_ticker = NotificationTicker(
            session_factory=session_factory,
            notifier=SelfrotBotNotifier(self.api),
            dialog_service=self.dialog_service,
        )
        self.moderation_ticker = ModerationTicker(
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
            daily_limit=settings.ROAST_DAILY_LIMIT,
            timeout=settings.ROAST_TIMEOUT,
        )
        tavily_key = settings.TAVILY_API_KEY.get_secret_value()
        self.search_service = SearchService(
            self.llm,
            TavilyClient(tavily_key),
            enabled=bool(tavily_key) and bool(api_key),
            model=settings.SEARCH_MODEL,
            daily_limit=settings.SEARCH_DAILY_LIMIT,
            cooldown=settings.SEARCH_COOLDOWN,
            timeout=settings.SEARCH_TIMEOUT,
        )
        tools = Path(settings.MEDIA_TOOLS_DIR)
        self.link_media_service = LinkMediaService(
            Downloader(tools, UPLOAD_LIMIT, settings.LINK_MEDIA_MAX_DURATION),
            session_factory,
            enabled=(tools / "yt-dlp").exists(),
        )
        self.music_service = MusicService(
            MusicFinder(tools, settings.MUSIC_MAX_DURATION),
            Recognizer(),
            session_factory,
            enabled=self.link_media_service.enabled,
        )
        self.media_tools_updater = MediaToolsUpdater(tools)
        self.duel_ticker = DuelTicker(
            session_factory=session_factory,
            bot=self.api,
            dialog_service=self.dialog_service,
            mob_service=self.mob_service,
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

    # Через propagate проходит каждый апдейт, и только он знает, какой хендлер сработал.
    # Упавший хендлер propagate пробрасывает исключением: сообщение всё равно считается.
    async def propagate(self, ctx: AppContext) -> BaseHandler[Any] | None:
        started = time.monotonic()
        handler = None
        try:
            handler = await super().propagate(ctx)
            return handler
        finally:
            self.observe(ctx, handler, time.monotonic() - started)

    def observe(self, ctx: AppContext, handler: BaseHandler[Any] | None, seconds: float) -> None:
        user, chat, event = ctx.user, ctx.chat, ctx.event
        if isinstance(event, Message) and user is not None and chat is not None:
            self.analytics.message(chat_id=chat.id, user_id=user.id, chat_type=chat.type)
        if handler is not None and getattr(handler, "counted", True):
            self.analytics.command(
                handler=type(handler).__name__,
                update_kind=type(event).__name__,
                user_id=user.id if user is not None else None,
                chat_id=chat.id if chat is not None else None,
                chat_type=chat.type if chat is not None else None,
                seconds=seconds,
            )

    def create_context(self, update: Update) -> AppContext:
        return self.context(
            update,
            self.api,
            dialog_service=self.dialog_service,
            session_factory=self.session_factory,
            ghoul_quiz_service=self.quiz_service,
            roast_service=self.roast_service,
            search_service=self.search_service,
            link_media_service=self.link_media_service,
            music_service=self.music_service,
            player_docs_service=self.player_docs,
            rp_commands_service=self.rp_commands_service,
            wordle_service=self.wordle_service,
            wikipedia_service=self.wikipedia_service,
            mob_service=self.mob_service,
            video_cutter_service=self.video_cutter_service,
            video_worker=self.video_worker,
        )

    async def on_startup(self) -> None:
        # Перед любым режимом старый вебхук снимается (иначе polling получит 409),
        # накопившиеся апдейты отбрасываются.
        await self.api.delete_webhook(drop_pending_updates=True)
        await self.video_worker.start()
        await self.notification_ticker.start()
        await self.moderation_ticker.start()
        await self.duel_ticker.start()
        await self.analytics_ticker.start()
        if settings.DOCS_CHANNEL:
            # Правка десятков постов упирается во флуд-контроль: запуск бота её не ждёт.
            task = asyncio.create_task(self.publish_docs(settings.DOCS_CHANNEL))
            self.alerts.add(task)
            task.add_done_callback(self.alerts.discard)
        if self.link_media_service.enabled:
            await self.media_tools_updater.start()
        self.roast_service.bot_id = (await self.api.get_me()).id
        await self.roast_service.cleanup()

    async def publish_docs(self, channel: str) -> None:
        try:
            report = await self.player_docs.publish(TelegramDocsChannel(self.api, channel), channel)
        except Exception:
            logger.exception("Документация в %s не опубликовалась", channel)
            return
        logger.info(
            "Документация в %s: новых %d, исправлено %d, удалено %d",
            channel,
            len(report.published),
            len(report.edited),
            len(report.deleted),
        )

    async def on_shutdown(self) -> None:
        await self.video_worker.stop()
        await self.notification_ticker.stop()
        await self.moderation_ticker.stop()
        await self.duel_ticker.stop()
        await self.analytics_ticker.stop()
        await self.analytics.flush()
        await self.media_tools_updater.stop()
        await self.quiz_service.close()
        await self.search_service.close()
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
