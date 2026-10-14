from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Command

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import TextMessage


class RandomEditHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("1000-7", prefixes="", args_count=0)

    async def handle(self) -> None:
        file_id = await self.ctx.ghoul_edit_repository.random_file_id()
        if file_id is None:
            await self.ctx.say(Dialogs.fun.edits.empty(), reply=True)
            return
        await self.ctx.message.reply_video(file_id, supports_streaming=True)


class EditsRouter(BaseRouter[AppContext]):
    handlers = (RandomEditHandler,)
