import logging

from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import Command

from src.bot.exceptions import MediaToolError

from ....context import AppContext
from ...types import TextMessage
from .tracks import MUSIC, track_keyboard

logger = logging.getLogger(__name__)


class SongArgs(CommandArgs):
    query: Rest = ""


class SongSearchHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("песня", SongArgs, prefixes="", ignore_case=True)
    query = cmd

    # Поиск через yt-dlp идёт секундами: в handle он держал бы сессию БД и слот диспетчера.
    asked = ""

    async def handle(self) -> None:
        if not self.ctx.music_service.enabled:
            return
        asked = self.cmd.parse(self.ctx).query.strip()
        if not asked:
            await self.ctx.say(MUSIC.usage(), reply=True)
            return
        self.asked = asked

    async def after_handle(self) -> None:
        if not self.asked:
            return
        try:
            await self.ctx.answer_chat_action("typing")
            tracks = await self.ctx.music_service.search(self.asked)
        except MediaToolError:
            logger.warning("Поиск песни %r не удался", self.asked, exc_info=True)
            await self.ctx.say(MUSIC.failed(), reply=True)
            return
        if not tracks:
            await self.ctx.say(MUSIC.not_found(query=self.asked), reply=True)
            return

        await self.ctx.message.reply(
            self.ctx.text(MUSIC.results(query=self.asked)),
            reply_markup=track_keyboard(self.ctx, tracks),
        )
