import logging

from selfrot import BaseRouter, MessageHandler
from selfrot.exceptions import TelegramAPIError, TelegramBadRequest, TelegramNetworkError
from selfrot.filter import HasUser, TextRegexp
from selfrot.types import (
    InputFile,
    InputMediaAudio,
    InputMediaPhoto,
    InputRichBlock,
    InputRichBlockAudio,
    InputRichBlockPhoto,
    InputRichBlockSlideshow,
    InputRichMessage,
    Message,
    RichBlock,
    RichBlockAudio,
    RichBlockPhoto,
    RichBlockSlideshow,
)

from src.bot.dialogs import Dialogs
from src.bot.exceptions import LinkMediaError, LinkMediaTooLarge
from src.bot.services.link_media import LINK, Video, find_links, media_key
from src.bot.types import CachedMedia, CachedSlideshow, CachedVideo

from ...context import AppContext
from ..types import TextUserMessage

logger = logging.getLogger(__name__)


class LinkMediaHandler(MessageHandler[AppContext[TextUserMessage]]):
    # TextRegexp сверяет с начала текста, а ссылка может стоять где угодно.
    query = TextRegexp(f"(?s).*?(?:{LINK.pattern})", LINK.flags) & HasUser()

    # Скачивание идёт до минут: в handle оно держало бы сессию БД и слот диспетчера.
    links: tuple[str, ...] = ()

    async def handle(self) -> None:
        if self.ctx.link_media_service.enabled:
            self.links = tuple(find_links(self.ctx.message.text))

    async def after_handle(self) -> None:
        for link in self.links:
            try:
                await self.send(link)
            except LinkMediaTooLarge:
                await self.ctx.say(Dialogs.link_media.too_large(), reply=True)
            except (LinkMediaError, TelegramAPIError, TelegramNetworkError):
                logger.warning("Медиа по ссылке %s не отправилось", link, exc_info=True)

    async def send(self, link: str) -> None:
        service = self.ctx.link_media_service
        url = await service.resolve(link)
        key = media_key(url)
        cached = await service.cached(key) if key else None
        if key and cached:
            try:
                await self.send_cached(cached)
                return
            except TelegramBadRequest:
                logger.info("file_id для %s устарел, качаю заново", key)
                await service.forget(key)

        await self.ctx.answer_chat_action("upload_video")
        async with service.media(url) as media:
            if isinstance(media, Video):
                sent: CachedMedia | None = await self.send_video(media)
            else:
                sent = await self.send_slideshow(media.images, media.audio, fresh=True)
        if key and sent:
            await service.remember(key, sent)

    async def send_cached(self, cached: CachedMedia) -> None:
        if isinstance(cached, CachedVideo):
            await self.ctx.message.reply_video(cached.file_id, supports_streaming=True)
        else:
            await self.send_slideshow(cached.photo_file_ids, cached.audio_file_id)

    async def send_video(self, video: Video) -> CachedVideo | None:
        sent = await self.ctx.message.reply_video(
            InputFile.from_path(video.path),
            width=video.width or None,
            height=video.height or None,
            duration=video.duration or None,
            thumbnail=InputFile.from_path(video.thumbnail) if video.thumbnail else None,
            supports_streaming=True,
        )
        return CachedVideo(sent.video.file_id) if sent.video else None

    async def send_slideshow(
        self, photos: tuple[str, ...], audio: str | None, *, fresh: bool = False
    ) -> CachedSlideshow | None:
        try:
            sent = await self.ctx.message.reply_rich_message(self.rich(photos, audio))
        except TelegramBadRequest:
            # Свежую ссылку на звук CDN может не отдать Telegram: тогда хотя бы картинки.
            if not fresh or audio is None:
                raise
            logger.info("Звук карусели не принят, отправляю без него", exc_info=True)
            sent = await self.ctx.message.reply_rich_message(self.rich(photos, None))
        return cached_slideshow(sent)

    def rich(self, photos: tuple[str, ...], audio: str | None) -> InputRichMessage:
        images: list[InputRichBlock] = [
            InputRichBlockPhoto(photo=InputMediaPhoto(media=photo)) for photo in photos
        ]
        blocks: list[InputRichBlock] = (
            [InputRichBlockSlideshow(blocks=images)] if len(images) > 1 else images
        )
        if audio is not None:
            blocks.append(InputRichBlockAudio(audio=InputMediaAudio(media=audio)))
        return InputRichMessage(blocks=blocks)


def cached_slideshow(message: Message) -> CachedSlideshow | None:
    photos: list[str] = []
    audio: str | None = None

    def walk(blocks: list[RichBlock]) -> None:
        nonlocal audio
        for block in blocks:
            if isinstance(block, RichBlockSlideshow):
                walk(block.blocks)
            elif isinstance(block, RichBlockPhoto) and block.photo:
                photos.append(block.photo[-1].file_id)
            elif isinstance(block, RichBlockAudio):
                audio = block.audio.file_id

    if message.rich_message is not None:
        walk(message.rich_message.blocks)
    return CachedSlideshow(tuple(photos), audio) if photos else None


class LinkMediaRouter(BaseRouter[AppContext]):
    handlers = (LinkMediaHandler,)
