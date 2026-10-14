import asyncio
import json
import logging
from pathlib import Path

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram.types import Message

logger = logging.getLogger(__name__)

# Telegram пересылает не больше 100 сообщений за раз.
FORWARD_BATCH = 100
# Пауза между пачками: досылка всей истории каналов не должна упереться в FloodWait.
BATCH_PAUSE = 2.0


# Последний пересланный id по каждому каналу — в state_path: при запуске досылается только
# то, что вышло, пока юзербот был выключен.
class EditsForwarder:
    def __init__(self, app: Client, channels: list[str], bot: str, state_path: Path) -> None:
        self.app = app
        self.channels = channels
        self.bot = bot
        self.state_path = state_path
        self.state: dict[str, int] = self._load_state()

    def _load_state(self) -> dict[str, int]:
        if not self.state_path.exists():
            return {}
        return {str(k): int(v) for k, v in json.loads(self.state_path.read_text()).items()}

    def _save(self, channel: str, last_id: int) -> None:
        if last_id <= self.state.get(channel, 0):
            return
        self.state[channel] = last_id
        self.state_path.write_text(json.dumps(self.state, indent=2))

    async def catch_up(self) -> None:
        for channel in self.channels:
            last = self.state.get(channel, 0)
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
                batch = missed[start : start + FORWARD_BATCH]
                await self.app.forward_messages(self.bot, channel, batch)
                self._save(channel, batch[-1])
                await asyncio.sleep(BATCH_PAUSE)

    def listen(self) -> None:
        chats: list[int | str] = [*self.channels]
        self.app.add_handler(MessageHandler(self._on_post, filters.chat(chats) & filters.video))

    async def _on_post(self, _: Client, message: Message) -> None:
        channel = self._channel_key(message)
        if channel is None:
            return
        await message.forward(self.bot)
        self._save(channel, message.id)
        logger.info("%s: переслан новый эдит %d", channel, message.id)

    def _channel_key(self, message: Message) -> str | None:
        names = {str(message.chat.id), (message.chat.username or "").lower()}
        return next(
            (channel for channel in self.channels if channel.lstrip("@").lower() in names), None
        )
