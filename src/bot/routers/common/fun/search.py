from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import HasUser

from src.bot.dialogs import Dialogs
from src.bot.exceptions import SearchCooldown, SearchLimitReached, SearchUnavailable

from ....context import AppContext
from ...types import TextUserMessage
from .commands import bot_command

SEARCH = Dialogs.fun.search


class SearchArgs(CommandArgs):
    query: Rest = ""


class SearchHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = bot_command("найди", SearchArgs)
    query = cmd & HasUser()
    usage = SEARCH.usage()

    # Поиск с ответом модели идёт секундами: в handle он держал бы сессию БД и слот диспетчера.
    asked: str | None = None

    async def handle(self) -> None:
        asked = self.cmd.parse(self.ctx).query.strip()
        if not asked:
            await self.ctx.say(self.usage, reply=True)
            return

        self.ctx.search_service.reserve(self.ctx.message.user.id)
        await self.ctx.answer_chat_action("typing")
        self.asked = asked

    async def after_handle(self) -> None:
        if self.asked is None:
            return

        found = await self.ctx.search_service.answer(self.asked)
        if found is None:
            await self.ctx.say(SEARCH.failed(), reply=True)
            return
        await self.ctx.message.reply(found)

    async def on_error(self, exc: Exception) -> None:
        match exc:
            case SearchCooldown(seconds=seconds):
                await self.ctx.say(SEARCH.cooldown(seconds=seconds), reply=True)
            case SearchLimitReached():
                await self.ctx.say(SEARCH.limit_reached(), reply=True)
            case SearchUnavailable():
                await self.ctx.say(SEARCH.unavailable(), reply=True)
            case _:
                raise exc
