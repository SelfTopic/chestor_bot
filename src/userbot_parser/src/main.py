import asyncio
import logging

import tgcrypto
from pyrogram.client import Client
from pyrogram.methods.utilities.idle import idle

from .config import config
from .edits import EditsForwarder
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

    if not (config.EDIT_CHANNELS and config.EDITS_BOT):
        await app.stop()
        return

    me = await app.get_me()
    logger.info("Эдиты: EDITS_USERBOT_ID для .env бота — %s", me.id)
    forwarder = EditsForwarder(app, config.EDIT_CHANNELS, config.EDITS_BOT, config.EDITS_STATE_PATH)
    forwarder.listen()
    await forwarder.catch_up()
    logger.info("Слушаю новые эдиты в %s", ", ".join(config.EDIT_CHANNELS))
    await idle()
    await app.stop()


_ = [tgcrypto]
asyncio.run(main())
