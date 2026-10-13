from typing import Annotated, Literal, Optional

from pydantic import BeforeValidator
from selfrot import CommandArgs, MessageHandler
from selfrot.filter import HasUser

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import WarnLimitOutOfRange
from src.bot.services.moderation import MAX_WARN_LIMIT, MIN_WARN_LIMIT
from src.bot.types import ChatRight, WarnPenalty

from ....context import AppContext
from ...types import TextUserMessage
from ..filters import FromChatAdmin
from ..flow import ModerationFlow, command
from .defaults import DefaultTermArgs, DefaultTermFlow


class WarnLimitArgs(CommandArgs):
    limit: Optional[int] = None


class WarnLimitHandler(ModerationFlow, MessageHandler[AppContext[TextUserMessage]]):
    right = ChatRight.CHANGE_INFO
    cmd = command("warn_limit", ("варн лимит", "пред лимит"), WarnLimitArgs)
    query = cmd & HasUser() & FromChatAdmin()

    def voiced_usage(self) -> Line:
        return self.phrases.warn_limit_current(
            limit=self.settings.warn_limit, min=MIN_WARN_LIMIT, max=MAX_WARN_LIMIT
        )

    async def handle(self) -> None:
        limit = self.cmd.parse(self.ctx).limit
        if limit is None:
            await self.ctx.say(self.voiced_usage(), reply=True)
            return

        await self.check_moderator()
        await self.ctx.moderation_service.set_warn_limit(self.ctx.message.chat.id, limit)
        await self.ctx.say(self.phrases.warn_limit_set(limit=limit), reply=True)
        self.report(
            self.phrases.log_warn_limit(
                chat=self.chat_title, moderator=self.moderator_name, limit=limit
            )
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, WarnLimitOutOfRange):
            line = self.phrases.warn_limit_out_of_range(
                min=exc.min_limit, max=exc.max_limit
            )
            await self.ctx.say(line, reply=True)
            return

        await super().on_error(exc)


PenaltyWord = Annotated[
    Literal["мут", "бан", "кик", "mute", "ban", "kick"], BeforeValidator(str.lower)
]

PENALTIES: dict[str, WarnPenalty] = {
    "мут": WarnPenalty.MUTE,
    "mute": WarnPenalty.MUTE,
    "бан": WarnPenalty.BAN,
    "ban": WarnPenalty.BAN,
    "кик": WarnPenalty.KICK,
    "kick": WarnPenalty.KICK,
}


def penalty_name(penalty: WarnPenalty) -> Line:
    match penalty:
        case WarnPenalty.MUTE:
            return Dialogs.moderation.penalty.mute()
        case WarnPenalty.BAN:
            return Dialogs.moderation.penalty.ban()
        case WarnPenalty.KICK:
            return Dialogs.moderation.penalty.kick()


class WarnPenaltyArgs(CommandArgs):
    penalty: Optional[PenaltyWord] = None


class WarnPenaltyHandler(ModerationFlow, MessageHandler[AppContext[TextUserMessage]]):
    right = ChatRight.CHANGE_INFO
    cmd = command("warn_action", ("варн наказание", "пред наказание"), WarnPenaltyArgs)
    query = cmd & HasUser() & FromChatAdmin()

    def voiced_usage(self) -> Line:
        name = self.ctx.text(penalty_name(self.settings.warn_penalty))
        return self.phrases.warn_penalty_current(penalty=name)

    async def handle(self) -> None:
        word = self.cmd.parse(self.ctx).penalty
        if word is None:
            await self.ctx.say(self.voiced_usage(), reply=True)
            return

        await self.check_moderator()
        penalty = PENALTIES[word]
        await self.ctx.moderation_service.set_warn_penalty(self.ctx.message.chat.id, penalty)
        name = self.ctx.text(penalty_name(penalty))
        await self.ctx.say(self.phrases.warn_penalty_set(penalty=name), reply=True)
        self.report(
            self.phrases.log_warn_penalty(
                chat=self.chat_title, moderator=self.moderator_name, penalty=name
            )
        )


class WarnExpiryHandler(DefaultTermFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = command("warn_expiry", ("варн срок", "пред срок"), DefaultTermArgs)
    query = cmd & HasUser() & FromChatAdmin()

    def term(self, seconds: Optional[int]) -> str:
        term = Dialogs.moderation.term
        if seconds is None:
            return self.ctx.text(term.never())
        return self.ctx.text(term.after(duration=self.duration(seconds)))

    def stored(self) -> Optional[int]:
        return self.settings.warn_expiry_seconds

    async def store(self, seconds: Optional[int]) -> None:
        chat_id = self.ctx.message.chat.id
        await self.ctx.moderation_service.set_warn_expiry(chat_id, seconds)

    def current(self, term: str) -> Line:
        return self.phrases.warn_expiry_current(term=term)

    def changed(self, term: str) -> Line:
        return self.phrases.warn_expiry_set(term=term)

    def logged(self, term: str) -> Line:
        return self.phrases.log_warn_expiry(
            chat=self.chat_title, moderator=self.moderator_name, term=term
        )
