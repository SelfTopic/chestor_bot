import logging

from selfrot import MessageHandler
from selfrot.exceptions import TelegramAPIError, TelegramNetworkError
from selfrot.filter import Command, HasReplyToMessage, HasUser
from selfrot.types import Message

from src.bot.exceptions import MediaToolError

from ....context import AppContext
from ...types import TextUserReplyToMessage
from .tracks import MUSIC, track_keyboard

logger = logging.getLogger(__name__)

SHAZAM = MUSIC.shazam
# Больше Bot API боту скачать не даёт.
DOWNLOAD_LIMIT = 20 * 1024 * 1024


def media_file(message: Message) -> tuple[str, int] | None:
    for media in (message.voice, message.video_note, message.video, message.audio):
        if media is not None:
            return media.file_id, media.file_size or 0
    document = message.document
    if document is not None and (document.mime_type or "").startswith(("audio/", "video/")):
        return document.file_id, document.file_size or 0
    return None


class ShazamHandler(MessageHandler[AppContext[TextUserReplyToMessage]]):
    query = (
        (
            Command("шазам", prefixes="", ignore_case=True, args_count=0)
            | Command("shazam", prefixes="", ignore_case=True, args_count=0)
        )
        & HasReplyToMessage()
        & HasUser()
    )

    # Скачивание и распознавание идут секундами: в handle держали бы сессию БД и слот.
    file_id = ""

    async def handle(self) -> None:
        if not self.ctx.music_service.enabled:
            return
        found = media_file(self.ctx.message.reply_to_message)
        if found is None:
            await self.ctx.say(SHAZAM.usage(), reply=True)
            return
        file_id, size = found
        if size > DOWNLOAD_LIMIT:
            await self.ctx.say(SHAZAM.too_big(), reply=True)
            return
        self.file_id = file_id

    async def after_handle(self) -> None:
        if not self.file_id:
            return
        service = self.ctx.music_service
        try:
            await self.ctx.answer_chat_action("typing")
            recognized = await service.recognize(await self.ctx.bot.download(self.file_id))
        except (MediaToolError, TelegramAPIError, TelegramNetworkError):
            logger.warning("Шазам не распознал %s", self.file_id, exc_info=True)
            await self.ctx.say(MUSIC.failed(), reply=True)
            return
        if recognized is None:
            await self.ctx.say(SHAZAM.not_recognized(), reply=True)
            return

        text = self.ctx.text(SHAZAM.recognized(title=recognized.title, artist=recognized.artist))
        try:
            tracks = await service.search(f"{recognized.artist} {recognized.title}")
        except MediaToolError:
            logger.warning("Поиск распознанной песни не удался", exc_info=True)
            tracks = []
        keyboard = track_keyboard(self.ctx, tracks) if tracks else None
        await self.ctx.message.reply(text, reply_markup=keyboard)
