"""
Отправка сообщений, без привязки к конкретной библиотеке Telegram. BroadcastService,
LevelUpService и NotificationTicker принимают Notifier, а не Bot: их бизнес-логика
(кому писать и что) от библиотеки не зависит и не должна зависеть — единственное место
во всех трёх, которое знает про selfrotgram, это SelfrotBotNotifier ниже.
"""

from pathlib import Path
from typing import Protocol

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError
from selfrot.types import InputFile


class NotifyError(Exception):
    """Сообщение не отправилось: собеседник недоступен, устаревший file_id и т.п.
    Не разделяется на подтипы — ни один вызывающий код в этих трёх сервисах не ведёт
    себя по-разному в зависимости от причины, только логирует и продолжает."""


class Notifier(Protocol):
    async def send_message(
        self, chat_id: int, text: str, *, parse_mode: str | None = None
    ) -> None: ...

    async def send_video(
        self, chat_id: int, video: str | Path, *, caption: str | None = None
    ) -> str:
        """video — file_id (str) или локальный путь. Возвращает file_id отправленного
        видео (Telegram всегда назначает его, даже при повторной загрузке того же
        файла) — по нему вызывающий код обновляет кеш, если прислал путь, а не id."""
        ...


class SelfrotBotNotifier:
    """Notifier поверх selfrot.Bot."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(
        self, chat_id: int, text: str, *, parse_mode: str | None = None
    ) -> None:
        try:
            await self._bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode
            )
        except TelegramAPIError as e:
            raise NotifyError(str(e)) from e

    async def send_video(
        self, chat_id: int, video: str | Path, *, caption: str | None = None
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
