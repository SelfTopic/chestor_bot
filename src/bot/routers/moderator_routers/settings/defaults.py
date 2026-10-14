from typing import Optional

from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import AnyCommand, HasUser

from src.bot.dialogs import Line
from src.bot.exceptions import DurationParseError
from src.bot.types import ChatRight

from ....context import AppContext
from ...types import TextUserMessage
from ..filters import FromChatAdmin
from ..flow import ModerationFlow, command


class DefaultTermArgs(CommandArgs):
    term: Rest = ""


class DefaultTermFlow(ModerationFlow):
    right = ChatRight.CHANGE_INFO
    cmd: AnyCommand[DefaultTermArgs]

    def stored(self) -> Optional[int]:
        raise NotImplementedError

    async def store(self, seconds: Optional[int]) -> None:
        raise NotImplementedError

    def current(self, term: str) -> Line:
        raise NotImplementedError

    def changed(self, term: str) -> Line:
        raise NotImplementedError

    def logged(self, term: str) -> Line:
        raise NotImplementedError

    # on_error идёт после отката сессии: настройки из БД там уже не прочитать.
    async def pre_handle(self) -> None:
        await super().pre_handle()
        self.stored_seconds = self.stored()

    def voiced_usage(self) -> Line:
        return self.current(self.term(self.stored_seconds))

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).term
        if not text:
            await self.ctx.say(self.voiced_usage(), reply=True)
            return

        await self.check_moderator()
        seconds = self.ctx.moderation_service.term(text)
        await self.store(seconds)
        term = self.term(seconds)
        await self.ctx.say(self.changed(term), reply=True)
        self.report(self.logged(term))

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, DurationParseError):
            await self.ctx.say(self.voiced_usage(), reply=True)
            return

        await super().on_error(exc)


class MuteDefaultHandler(DefaultTermFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = command("mute_default", "мут дефолт", DefaultTermArgs)
    query = cmd & HasUser() & FromChatAdmin()

    def stored(self) -> Optional[int]:
        return self.settings.mute_default_seconds

    async def store(self, seconds: Optional[int]) -> None:
        chat_id = self.ctx.message.chat.id
        await self.ctx.moderation_service.set_mute_default(chat_id, seconds)

    def current(self, term: str) -> Line:
        return self.phrases.mute_default_current(term=term)

    def changed(self, term: str) -> Line:
        return self.phrases.mute_default_set(term=term)

    def logged(self, term: str) -> Line:
        return self.phrases.log_mute_default(
            chat=self.chat_title, moderator=self.moderator_name, term=term
        )


class BanDefaultHandler(DefaultTermFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = command("ban_default", "бан дефолт", DefaultTermArgs)
    query = cmd & HasUser() & FromChatAdmin()

    def stored(self) -> Optional[int]:
        return self.settings.ban_default_seconds

    async def store(self, seconds: Optional[int]) -> None:
        chat_id = self.ctx.message.chat.id
        await self.ctx.moderation_service.set_ban_default(chat_id, seconds)

    def current(self, term: str) -> Line:
        return self.phrases.ban_default_current(term=term)

    def changed(self, term: str) -> Line:
        return self.phrases.ban_default_set(term=term)

    def logged(self, term: str) -> Line:
        return self.phrases.log_ban_default(
            chat=self.chat_title, moderator=self.moderator_name, term=term
        )
