from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from .middlewares import (
    LoggingMiddleware,
    DatabaseMiddleware,
    SyncEntitiesMiddleware
)

from .routers.routes import include_routers
from .containers import Container
from ..database import session_factory, flush_database, engine

import asyncio
import dotenv
import os 
import sys
import logging
import colorlog 

def setup_colored_logging():
    console_format = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    file_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
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

# Configure envirion loading 
dotenv.load_dotenv()

# Getting token of bot from .env file
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    logger.fatal("Bot token is not found")
    sys.exit(1)


# Main point
async def main(bot_token: str) -> None:

    # Initialize a bot 
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(
            link_preview_is_disabled=True    
        )
    )
    logger.info("Object of bot is initialize")


    # Configure depedency injector container
    container = Container(bot=bot)
    container.wire(
        modules=[__name__], packages=[".routers", ".middlewares"]
    )

    # Initialize a dispatcher
    dp = Dispatcher()
    logger.info("Object of dispatcher is initialize")

    
    # Use dispactcher all middlewares
    dp.update.middleware(LoggingMiddleware())

    database_middleware = DatabaseMiddleware(session_factory=session_factory)
    dp.update.middleware(database_middleware)
    dp.update.middleware(SyncEntitiesMiddleware())

    # Include all routers in the dispatcher 
    include_routers(dp)

    # Reset data of database (dev)
    await flush_database(engine=engine)

    try:
        # Start bot on poolling
        logger.info("Starting polling of updates")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error polling: {e}")

    finally: 
        await bot.close()
        logger.info("Bot session is closed")


if __name__ == '__main__':
    try:
        logger.info("Run async main function")
        asyncio.run(main(BOT_TOKEN))

    except KeyboardInterrupt:
        logger.info("Bot stopped of ctrl + c")

    except Exception as e:
        logger.error(f"Error with start main function: {e}")

    finally: 
        logger.info("Programm finished")