import asyncio
import logging

import tgcrypto
from pyrogram.client import Client

from .config import config
from .parser import TelegramParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Client(
    name="userbot_parser",
    api_hash=config.API_HASH,
    api_id=config.API_ID,
    phone_number=config.PHONE_NUMBER,
    password=config.PASSWORD,
)


async def main():
    logger.info("Starting Telegram Parser...")
    parser = TelegramParser(app)

    await parser.parse_channel()
    logger.info("Parsing completed.")


_ = [tgcrypto]
asyncio.run(main())
