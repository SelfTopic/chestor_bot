import asyncio
import logging
import sys

import colorlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from src.config import settings

from ..database import create_tables, engine, flush_database, session_factory
from .containers import Container
from .middlewares import (
    BanMiddleware,
    DatabaseMiddleware,
    LoggingMiddleware,
    SyncEntitiesMiddleware,
)
from .routers.routes import include_routers


def setup_colored_logging():
    console_format = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )

    file_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_format)

    file_handler = logging.FileHandler("logs.log")
    file_handler.setFormatter(file_format)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logging.getLogger(__name__)


logger = setup_colored_logging()


if not settings.BOT_TOKEN:
    logger.fatal("Bot token is not found")
    sys.exit(1)


logger.info(f"ENV is {'PROD' if settings.ENV else 'DEV'}")

WEBHOOK_HOST = "https://chestor.site"
WEBHOOK_PATH = f"/webhook/{settings.BOT_TOKEN.get_secret_value()}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"


async def on_startup(bot: Bot):
    await bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"],
    )


async def main(bot_token: str, env: str) -> None:
    ENV = False if env == "DEV" else True
    bot = Bot(
        token=bot_token, default=DefaultBotProperties(link_preview_is_disabled=True)
    )

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Object of bot is initialize")

    container = Container(bot=bot)
    container.wire(
        modules=[__name__],
        packages=[
            "src.bot.routers",
            "src.bot.routers.common",
            "src.bot.routers.chat_member_update_routers",
            "src.bot.routers.creator_routers",
            "src.bot.routers.ghoul_routers",
            "src.bot.routers.moderator_routers",
            "src.bot.middlewares",
        ],
    )

    dp = Dispatcher()
    logger.info("Object of dispatcher is initialize")

    dp.update.middleware(LoggingMiddleware())

    database_middleware = DatabaseMiddleware(session_factory=session_factory)
    dp.update.middleware(database_middleware)
    dp.update.middleware(BanMiddleware())
    dp.update.middleware(SyncEntitiesMiddleware())

    include_routers(dp)

    if not ENV:
        await flush_database(engine=engine)
    else:
        await create_tables(engine=engine)

    if ENV:
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )

        app = web.Application()

        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        dp.startup.register(on_startup)

        runner = web.AppRunner(app)

        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=8999)

        try:
            await site.start()
            await asyncio.Event().wait()
        finally:
            await bot.session.close()
            await runner.cleanup()
            logger.info("Bot session and server closed")

    else:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(
                bot,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "chat_member",
                    "my_chat_member",
                ],
            )

        except Exception as e:
            logger.error(f"Error start bot: {e}")


if __name__ == "__main__":
    try:
        logger.info("Run async main function")
        asyncio.run(main(settings.BOT_TOKEN.get_secret_value(), settings.ENV))

    except KeyboardInterrupt:
        logger.info("Bot stopped of ctrl + c")

    except Exception as e:
        logger.error(f"Error with start main function: {e}")

    finally:
        logger.info("Programm finished")
