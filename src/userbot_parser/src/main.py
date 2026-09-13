import asyncio
import logging

import tgcrypto
from pyrogram.client import Client

from .config import config
from .parser import TelegramParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Client создаётся здесь, а не на уровне модуля - Client.__init__
    # делает self.loop = asyncio.get_event_loop(), а на уровне модуля
    # (до asyncio.run) это НЕ тот loop, что реально будет исполнять main().
    # Раньше это давало "attached to a different loop" при app.stop().
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
