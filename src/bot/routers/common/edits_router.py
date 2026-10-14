import json
import logging
from typing import Any

from selfrot import BaseContext, BaseRouter, MessageHandler
from selfrot.filter import BaseFilter, Command, HasForwardOrigin, HasUser, HasVideo
from selfrot.types import ForwardOriginMessage, MessageOriginChannel, UserMessage, VideoMessage

from src.bot.dialogs import Dialogs
from src.config import settings

from ...context import AppContext
from ..types import TextMessage

logger = logging.getLogger(__name__)


class ForwardedVideoMessage(VideoMessage, ForwardOriginMessage, UserMessage, frozen=True):
    pass


class FromEditsUserbot(BaseFilter[AppContext[Any]]):
    async def check(self, ctx: BaseContext[Any]) -> bool:
        user = ctx.user
        return (
            settings.EDITS_USERBOT_ID != 0
            and user is not None
            and user.id == settings.EDITS_USERBOT_ID
        )


class EditForwardedHandler(MessageHandler[AppContext[ForwardedVideoMessage]]):
    query = HasVideo() & HasForwardOrigin() & HasUser() & FromEditsUserbot()

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
class EditsSyncHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("edits_sync", args_count=0) & FromEditsUserbot()

    async def handle(self) -> None:
        last = await self.ctx.ghoul_edit_repository.last_posts()
        await self.ctx.message.answer(f"edits_sync {json.dumps(last)}")


class RandomEditHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("1000-7", prefixes="", args_count=0)

    async def handle(self) -> None:
        file_id = await self.ctx.ghoul_edit_repository.random_file_id()
        if file_id is None:
            await self.ctx.say(Dialogs.fun.edits.empty(), reply=True)
            return
        await self.ctx.message.reply_video(file_id, supports_streaming=True)


class EditsRouter(BaseRouter[AppContext]):
    handlers = (EditForwardedHandler, EditsSyncHandler, RandomEditHandler)
