import logging
from textwrap import shorten

from selfrot import CallbackPayload, InlineKeyboard, button
from selfrot.exceptions import TelegramAPIError, TelegramBadRequest, TelegramNetworkError
from selfrot.filter import HasMessageCallbackQuery
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import InlineKeyboardMarkup, InputFile, Message

from src.bot.dialogs import Dialogs
from src.bot.exceptions import MediaToolError
from src.bot.services.music import Audio, Track

from ....context import AppContext
from ...types import DataMessageCallbackQuery

logger = logging.getLogger(__name__)

MUSIC = Dialogs.music
# Длинное название не помещается на кнопку в телефоне.
TITLE_WIDTH = 40


class TrackPick(CallbackPayload, prefix="song"):
    track_id: str


def track_keyboard(ctx: AppContext[object], tracks: list[Track]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()
    for track in tracks:
        minutes, seconds = divmod(track.duration, 60)
        label = MUSIC.button(
            title=shorten(track.title, TITLE_WIDTH, placeholder="…"),
            author=shorten(track.author, TITLE_WIDTH // 2, placeholder="…"),
            duration=f"{minutes}:{seconds:02}",
        )
        keyboard.row(button(ctx.text(label), TrackPick(track_id=track.id)))
    return keyboard.markup()


class TrackPickHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    pick = TrackPick.filter()
    query = pick & HasMessageCallbackQuery()

    track_id = ""

    async def handle(self) -> None:
        self.track_id = self.pick.parse(self.ctx).track_id
        await self.ctx.callback_query.answer(self.ctx.text(MUSIC.downloading()))

    async def after_handle(self) -> None:
        message = self.ctx.callback_query.message
        if not self.track_id or not isinstance(message, Message):
            return
        try:
            await self.send(message)
        except (MediaToolError, TelegramAPIError, TelegramNetworkError):
            logger.warning("Трек %s не отправился", self.track_id, exc_info=True)
            await message.reply(self.ctx.text(MUSIC.failed()))

    async def send(self, message: Message) -> None:
        service = self.ctx.music_service
        cached = await service.cached(self.track_id)
        if cached is not None:
            try:
                await message.reply_audio(cached)
                return
            except TelegramBadRequest:
                logger.info("file_id трека %s устарел, качаю заново", self.track_id)
                await service.forget(self.track_id)

        await self.ctx.answer_chat_action("upload_voice")
        async with service.audio(self.track_id) as audio:
            sent = await self.reply_audio(message, audio)
        if sent.audio is not None:
            await service.remember(self.track_id, sent.audio.file_id)

    async def reply_audio(self, message: Message, audio: Audio) -> Message:
        return await message.reply_audio(
            InputFile.from_path(audio.path),
            title=audio.title or None,
            performer=audio.performer or None,
            duration=audio.duration or None,
            thumbnail=InputFile.from_path(audio.thumbnail) if audio.thumbnail else None,
        )
