import logging

from selfrot import BaseRouter, MessageHandler
from selfrot.exceptions import TelegramAPIError, TelegramNetworkError
from selfrot.filter import HasUser, TextRegexp
from selfrot.types import InputFile, InputMediaPhoto

from src.bot.dialogs import Dialogs
from src.bot.exceptions import LinkMediaError, LinkMediaTooLarge
from src.bot.services.link_media import LINK, Slideshow, Video, find_links

from ...context import AppContext
from ..types import TextUserMessage

logger = logging.getLogger(__name__)

# Больше фото в одном альбоме Telegram не принимает.
ALBUM_LIMIT = 10


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
            await self.send(link)

    async def send(self, link: str) -> None:
        service = self.ctx.link_media_service
        try:
            await self.ctx.answer_chat_action("upload_video")
            async with service.media(link) as media:
                if isinstance(media, Video):
                    await self.reply_video(media)
                else:
                    await self.reply_slideshow(media)
        except LinkMediaTooLarge:
            await self.ctx.say(Dialogs.link_media.too_large(), reply=True)
        except (LinkMediaError, TelegramAPIError, TelegramNetworkError):
            logger.warning("Медиа по ссылке %s не отправилось", link, exc_info=True)

    async def reply_video(self, video: Video) -> None:
        await self.ctx.message.reply_video(
            InputFile.from_path(video.path),
            width=video.width or None,
            height=video.height or None,
            duration=video.duration or None,
            thumbnail=InputFile.from_path(video.thumbnail) if video.thumbnail else None,
            supports_streaming=True,
        )

    async def reply_slideshow(self, slideshow: Slideshow) -> None:
        message = self.ctx.message
        images = slideshow.images
        for start in range(0, len(images), ALBUM_LIMIT):
            chunk = images[start : start + ALBUM_LIMIT]
            if len(chunk) == 1:
                await message.reply_photo(chunk[0])
            else:
                await message.reply_media_group([InputMediaPhoto(media=url) for url in chunk])
        if slideshow.audio is not None:
            await message.reply_audio(InputFile.from_path(slideshow.audio))


class LinkMediaRouter(BaseRouter[AppContext]):
    handlers = (LinkMediaHandler,)
