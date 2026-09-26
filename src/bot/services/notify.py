from pathlib import Path
from typing import Protocol

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError
from selfrot.types import InputFile


class NotifyError(Exception):
    pass
class Notifier(Protocol):
    async def send_message(
        self, chat_id: int, text: str, *, parse_mode: str | None = None
    ) -> None: ...

    async def send_video(
        self, chat_id: int, video: str | Path, *, caption: str | None = None
    ) -> str:
        ...


class SelfrotBotNotifier:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> None:
        try:
            await self._bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode
            )
        except TelegramAPIError as e:
            raise NotifyError(str(e)) from e

    async def send_video(
        self,
        chat_id: int,
        video: str | Path,
        *,
        caption: str | None = None,
    ) -> str:
        source = video if isinstance(video, str) else InputFile.from_path(video)
        try:
            sent = await self._bot.send_video(
                chat_id=chat_id, video=source, caption=caption
            )
        except TelegramAPIError as e:
            raise NotifyError(str(e)) from e

        if sent.video is None:
            raise NotifyError("Telegram не вернул video в ответе send_video")

        return sent.video.file_id
