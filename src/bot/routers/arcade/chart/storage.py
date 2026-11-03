from pathlib import Path

from selfrot import Bot
from selfrot.types import InputFile


# Telegram выдаёт file_id только за отправленное сообщение: файл уходит в закрытый канал.
# Сообщения остаются в канале: по ним видно, как идёт прогрев.
class TelegramChartStorage:
    def __init__(self, bot: Bot, chat_id: int) -> None:
        self._bot = bot
        self._chat_id = chat_id

    async def video(self, path: Path) -> str:
        sent = await self._bot.send_animation(
            self._chat_id, InputFile.from_path(path), disable_notification=True
        )
        assert sent.animation is not None
        return sent.animation.file_id

    async def picture(self, png: bytes) -> str:
        sent = await self._bot.send_photo(
            self._chat_id, InputFile(png, "chart.png"), disable_notification=True
        )
        assert sent.photo
        return sent.photo[-1].file_id
