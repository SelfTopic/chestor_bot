import json
import logging
import re
from typing import Any

from selfrot import BaseContext, BaseRouter, MessageHandler
from selfrot.filter import BaseFilter, Command, HasForwardOrigin, HasUser, HasVideo
from selfrot.types import (
    ForwardOriginMessage,
    Message,
    MessageOriginChannel,
    UserMessage,
    VideoMessage,
)

from src.config import settings

from ...context import AppContext
from ..types import TextMessage

logger = logging.getLogger(__name__)

# Подпись постов с сериями в канале аниме: «Токийский гуль 1 сезон 12. Название».
EPISODE_CAPTION = re.compile(r"Токийский гуль\s+(\d+)\s+сезон\s+(\d+)\.")


class ForwardedVideoMessage(VideoMessage, ForwardOriginMessage, UserMessage, frozen=True):
    pass


class FromUserbot(BaseFilter[AppContext[Any]]):
    async def check(self, ctx: BaseContext[Any]) -> bool:
        user = ctx.user
        return settings.USERBOT_ID != 0 and user is not None and user.id == settings.USERBOT_ID


class EpisodeCaption(BaseFilter[AppContext[Any]]):
    def episode(self, ctx: BaseContext[Any]) -> tuple[int, int] | None:
        message = ctx.event
        caption = message.caption if isinstance(message, Message) else None
        found = EPISODE_CAPTION.search(caption or "")
        return (int(found[1]), int(found[2])) if found else None

    async def check(self, ctx: BaseContext[Any]) -> bool:
        return self.episode(ctx) is not None


FORWARDED = HasVideo() & HasForwardOrigin() & HasUser() & FromUserbot()


class EpisodeForwardedHandler(MessageHandler[AppContext[ForwardedVideoMessage]]):
    caption = EpisodeCaption()
    query = FORWARDED & caption

    async def handle(self) -> None:
        message = self.ctx.message
        origin = message.forward_origin
        found = self.caption.episode(self.ctx)
        if not isinstance(origin, MessageOriginChannel) or found is None:
            return

        season, episode = found
        await self.ctx.anime_episode_repository.save(
            season, episode, message.video.file_id, origin.chat.id, origin.message_id
        )
        logger.info("Серия %s×%s: пост %s канала %s", season, episode, origin.message_id, origin.chat.id)


class EditForwardedHandler(MessageHandler[AppContext[ForwardedVideoMessage]]):
    query = FORWARDED

    async def handle(self) -> None:
        message = self.ctx.message
        origin = message.forward_origin
        if not isinstance(origin, MessageOriginChannel):
            return

        added = await self.ctx.ghoul_edit_repository.add(
            message.video.file_id,
            message.video.file_unique_id,
            origin.chat.id,
            origin.message_id,
        )
        if added:
            logger.info("Новый эдит: пост %s канала %s", origin.message_id, origin.chat.id)


# Ответ юзерботу, а не людям: по нему он досылает посты, которые не дошли до бота
# (например, пришли, пока бот перезапускался и выбросил накопившиеся апдейты).
class SyncHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("userbot_sync", args_count=0) & FromUserbot()

    async def handle(self) -> None:
        last = await self.ctx.ghoul_edit_repository.last_posts()
        for channel, post in (await self.ctx.anime_episode_repository.last_posts()).items():
            last[channel] = max(post, last.get(channel, 0))
        await self.ctx.message.answer(f"userbot_sync {json.dumps(last)}")


class UserbotInboxRouter(BaseRouter[AppContext]):
    handlers = (EpisodeForwardedHandler, EditForwardedHandler, SyncHandler)
