from pathlib import Path
from typing import Protocol

from selfrot import Bot
# Сервисы берут упоминание отсюда: notify.py — их единственный вход в selfrot.
from selfrot import mention_html as mention_html
from selfrot.exceptions import MessageNotModified, TelegramAPIError
from selfrot.types import InputFile, InputRichMessage


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


class DocsChannel(Protocol):
    async def publish(self, markdown: str) -> int: ...

    async def edit(self, message_id: int, markdown: str) -> None: ...

    async def delete(self, message_id: int) -> None: ...

    async def pin(self, message_id: int) -> None: ...

    def link(self, message_id: int) -> str: ...


# Канал документации: посты — rich-сообщения из Markdown, Telegram сам строит из него блоки.
class TelegramDocsChannel:
    def __init__(self, bot: Bot, channel: str) -> None:
        self._bot = bot
        self._channel = channel

    async def publish(self, markdown: str) -> int:
        try:
            sent = await self._bot.send_rich_message(
                chat_id=self._channel, rich_message=InputRichMessage(markdown=markdown)
            )
        except TelegramAPIError as e:
            raise NotifyError(str(e)) from e
        return sent.message_id

    async def edit(self, message_id: int, markdown: str) -> None:
        try:
            await self._bot.edit_message_text(
                chat_id=self._channel,
                message_id=message_id,
                rich_message=InputRichMessage(markdown=markdown),
            )
        except MessageNotModified:
            pass
        except TelegramAPIError as e:
            raise NotifyError(str(e)) from e

    async def delete(self, message_id: int) -> None:
        try:
            await self._bot.delete_message(chat_id=self._channel, message_id=message_id)
        except TelegramAPIError as e:
            raise NotifyError(str(e)) from e

    async def pin(self, message_id: int) -> None:
        try:
            await self._bot.pin_chat_message(
                chat_id=self._channel, message_id=message_id, disable_notification=True
            )
        except TelegramAPIError as e:
            raise NotifyError(str(e)) from e

    def link(self, message_id: int) -> str:
        return post_link(self._channel, message_id)


def post_link(channel: str, message_id: int) -> str:
    return f"https://t.me/{channel.lstrip('@')}/{message_id}"
