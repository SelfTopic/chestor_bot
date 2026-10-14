import logging

from selfrot import BaseRouter, MessageHandler
from selfrot.exceptions import TelegramAPIError, TelegramNetworkError
from selfrot.filter import HasUser, TextRegexp
from selfrot.types import InputFile

from src.bot.dialogs import Dialogs
from src.bot.exceptions import LinkMediaError, LinkMediaTooLarge
from src.bot.services.link_media import LINK, Video, find_links

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
            await self.send(link)

    async def send(self, link: str) -> None:
        service = self.ctx.link_media_service
        try:
            await self.ctx.answer_chat_action("upload_video")
            async with service.video(link) as video:
                await self.reply_video(video)
        except LinkMediaTooLarge:
            await self.ctx.say(Dialogs.link_media.too_large(), reply=True)
        except (LinkMediaError, TelegramAPIError, TelegramNetworkError):
            logger.warning("Видео по ссылке %s не отправилось", link, exc_info=True)

    async def reply_video(self, video: Video) -> None:
        await self.ctx.message.reply_video(
            InputFile.from_path(video.path),
            width=video.width or None,
            height=video.height or None,
            duration=video.duration or None,
            thumbnail=InputFile.from_path(video.thumbnail) if video.thumbnail else None,
            supports_streaming=True,
        )


class LinkMediaRouter(BaseRouter[AppContext]):
    handlers = (LinkMediaHandler,)
