import asyncio
import logging

import tgcrypto
from pyrogram.client import Client
from pyrogram.methods.utilities.idle import idle
from pyrogram.types import Message

from .config import config
from .forwarder import ChannelForwarder, Wanted
from .parser import CAPTION_PATTERN, TelegramParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def any_video(_: Message) -> bool:
    return True


def episode_post(message: Message) -> bool:
    return CAPTION_PATTERN.search(message.caption or "") is not None


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

    if not config.BOT_USERNAME:
        await app.stop()
        return

    me = await app.get_me()
    logger.info("USERBOT_ID для .env бота — %s", me.id)
    sources: dict[str, Wanted] = {channel: any_video for channel in config.EDIT_CHANNELS}
    sources[str(config.CHANNEL_ID)] = episode_post
    forwarder = ChannelForwarder(app, sources, config.BOT_USERNAME)
    forwarder.listen()
    logger.info("Пересылаю боту %s посты из %s", config.BOT_USERNAME, ", ".join(sources))
    sync = asyncio.create_task(forwarder.run())
    await idle()
    sync.cancel()
    await app.stop()


_ = [tgcrypto]
asyncio.run(main())
