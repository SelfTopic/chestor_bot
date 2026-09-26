import asyncio
import logging

import tgcrypto
from pyrogram.client import Client

from .config import config
from .parser import TelegramParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Client создаётся внутри main: в __init__ он берёт текущий event loop, а на уровне
    # модуля это не тот loop, что у asyncio.run.
    app = Client(
        name="userbot_parser",
        api_hash=config.API_HASH,
        api_id=config.API_ID,
        phone_number=config.PHONE_NUMBER,
        password=config.PASSWORD,
    )

    await app.start()
    logger.info("Starting Telegram Parser...")
    parser = TelegramParser(app)

    await parser.parse_channel()
    logger.info("Parsing completed.")

    await app.stop()


_ = [tgcrypto]
asyncio.run(main())
