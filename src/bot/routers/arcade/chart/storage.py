import logging
from pathlib import Path

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError
from selfrot.types import InputFile, Message

logger = logging.getLogger(__name__)


# Telegram выдаёт file_id только за отправленное сообщение: файл уходит в закрытый канал,
# а сообщение сразу удаляется — file_id остаётся рабочим.
class TelegramChartStorage:
    def __init__(self, bot: Bot, chat_id: int) -> None:
        self._bot = bot
        self._chat_id = chat_id

    async def video(self, path: Path) -> str:
        sent = await self._bot.send_animation(
            self._chat_id, InputFile.from_path(path), disable_notification=True
        )
        assert sent.animation is not None
        await self._delete(sent)
        return sent.animation.file_id

    async def picture(self, png: bytes) -> str:
        sent = await self._bot.send_photo(
            self._chat_id, InputFile(png, "chart.png"), disable_notification=True
        )
        assert sent.photo
        await self._delete(sent)
        return sent.photo[-1].file_id

    async def _delete(self, message: Message) -> None:
        try:
            await self._bot.delete_message(self._chat_id, message.message_id)
        except TelegramAPIError:
            logger.warning("Не удалилось сообщение %s в канале «Джета»", message.message_id)
