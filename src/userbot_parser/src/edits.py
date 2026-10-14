import asyncio
import json
import logging

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram.types import Chat, Message

logger = logging.getLogger(__name__)

SYNC_COMMAND = "/edits_sync"
SYNC_REPLY = "edits_sync "
# Бот при старте выбрасывает накопившиеся апдейты, поэтому запрос повторяется, пока он
# не поднимется и не ответит.
SYNC_RETRY = 30.0
# Сверка досылает и живые посты, пересланные, пока бот перезапускался.
SYNC_INTERVAL = 3600.0
# Telegram пересылает не больше 100 сообщений за раз.
FORWARD_BATCH = 100
# Пауза между пачками: досылка всей истории каналов не должна упереться в FloodWait.
BATCH_PAUSE = 2.0


# Что уже дошло, знает только бот: он отвечает на SYNC_COMMAND последним сохранённым
# постом по каждому каналу, юзербот досылает всё, что новее.
class EditsForwarder:
    def __init__(self, app: Client, channels: list[str], bot: str) -> None:
        self.app = app
        self.channels = channels
        self.bot = bot
        self._reply: asyncio.Future[dict[int, int]] | None = None

    def listen(self) -> None:
        chats: list[int | str] = [*self.channels]
        self.app.add_handler(MessageHandler(self._on_post, filters.chat(chats) & filters.video))
        self.app.add_handler(
            MessageHandler(self._on_bot_reply, filters.chat(self.bot) & filters.text)
        )

    async def run(self) -> None:
        while True:
            try:
                await self._catch_up(await self._last_posts())
            except Exception:
                logger.exception("Сверка эдитов с ботом не удалась")
            await asyncio.sleep(SYNC_INTERVAL)

    async def _last_posts(self) -> dict[int, int]:
        self._reply = asyncio.get_running_loop().create_future()
        while True:
            await self.app.send_message(self.bot, SYNC_COMMAND)
            try:
                return await asyncio.wait_for(asyncio.shield(self._reply), SYNC_RETRY)
            except TimeoutError:
                logger.info("Бот %s пока не ответил на сверку, повторяю", self.bot)

    async def _on_bot_reply(self, _: Client, message: Message) -> None:
        text = message.text or ""
        if not text.startswith(SYNC_REPLY) or self._reply is None or self._reply.done():
            return
        last = json.loads(text.removeprefix(SYNC_REPLY))
        self._reply.set_result({int(channel): int(post) for channel, post in last.items()})

    async def _catch_up(self, last_posts: dict[int, int]) -> None:
        for channel in self.channels:
            chat = await self.app.get_chat(channel)
            if not isinstance(chat, Chat):
                logger.warning("%s: аккаунт не подписан на канал, пропускаю", channel)
                continue
            last = last_posts.get(chat.id, 0)
            missed: list[int] = []
            # Pyrogram объявляет асинхронный генератор как корутину.
            async for message in self.app.get_chat_history(channel):  # pyright: ignore[reportGeneralTypeIssues]
                if message.id <= last:
                    break
                if message.video:
                    missed.append(message.id)
            missed.reverse()
            logger.info("%s: к пересылке %d эдитов", channel, len(missed))

            for start in range(0, len(missed), FORWARD_BATCH):
                await self.app.forward_messages(
                    self.bot, channel, missed[start : start + FORWARD_BATCH]
                )
                await asyncio.sleep(BATCH_PAUSE)

    async def _on_post(self, _: Client, message: Message) -> None:
        await message.forward(self.bot)
        logger.info(
            "%s: переслан новый эдит %d", message.chat.username or message.chat.id, message.id
        )
