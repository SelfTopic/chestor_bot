from typing import Any, TypeVar

from selfrot import CommandArgs
from selfrot.exceptions import CommandArgsError
from selfrot.filter import AnyCommand, Command
from selfrot.types import ChatMember, ChatMemberAdministrator, ChatMemberOwner

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import (
    AnonymousModerator,
    BotLacksRight,
    ModeratorLacksRight,
    TermOutOfRange,
)
from src.bot.types import ChatRight, ModerationVoice
from src.bot.utils import parse_seconds

from ...context import AppContext
from .filters import is_anonymous_admin

TArgs = TypeVar("TArgs", bound=CommandArgs)


def command(slash: str, text: str, args: type[TArgs]) -> AnyCommand[TArgs]:
    return AnyCommand(
        Command(slash, args, ignore_case=True),
        Command(text, args, prefixes="", ignore_case=True),
    )


def has_right(member: ChatMember | None, right: ChatRight) -> bool:
    if isinstance(member, ChatMemberOwner):
        return True
    if not isinstance(member, ChatMemberAdministrator):
        return False

    match right:
        case ChatRight.RESTRICT_MEMBERS:
            return member.can_restrict_members
        case ChatRight.CHANGE_INFO:
            return member.can_change_info


def right_name(right: ChatRight) -> Line:
    match right:
        case ChatRight.RESTRICT_MEMBERS:
            return Dialogs.moderation.right.restrict_members()
        case ChatRight.CHANGE_INFO:
            return Dialogs.moderation.right.change_info()


# Миксин ставится первым основанием: его on_error, not_found и reply_errors должны
# перекрыть одноимённые у миксинов из routers/targeting.py.
class ModerationFlow:
    ctx: AppContext[Any]
    right: ChatRight
    voice = ModerationVoice.NEUTRAL
    reply_errors = True

    @property
    def phrases(self):
        if self.voice is ModerationVoice.ROUGH:
            return Dialogs.moderation.rough
        return Dialogs.moderation.neutral

    def voiced_usage(self) -> Line:
        raise NotImplementedError

    async def pre_handle(self) -> None:
        settings = await self.ctx.moderation_service.settings(self.ctx.message.chat.id)
        self.settings = settings
        self.voice = settings.voice

    async def check_moderator(self) -> int:
        message = self.ctx.message
        if is_anonymous_admin(message):
            raise AnonymousModerator()

        administrators = await self.ctx.chat_administrators()
        moderator = next(
            (a for a in administrators if a.user.id == message.user.id), None
        )
        if not has_right(moderator, self.right):
            raise ModeratorLacksRight(self.right)

        return message.user.id

    def duration(self, seconds: int) -> str:
        parts = parse_seconds(seconds)
        term = Dialogs.moderation.term
        units = (
            (parts.days, term.days),
            (parts.hours_remaining, term.hours),
            (parts.minutes_remaining, term.minutes),
            (parts.seconds_remaining, term.seconds),
        )
        return " ".join(
            self.ctx.text(unit(count=count)) for count, unit in units if count
        )

    def term(self, seconds: int | None) -> str:
        if seconds is None:
            return self.ctx.text(Dialogs.moderation.term.forever())
        return self.ctx.text(
            Dialogs.moderation.term.limited(duration=self.duration(seconds))
        )

    async def on_error(self, exc: Exception) -> None:
        phrases = self.phrases
        match exc:
            case CommandArgsError():
                line = self.voiced_usage()
            case AnonymousModerator():
                line = phrases.anonymous()
            case ModeratorLacksRight(right=right):
                line = phrases.moderator_lacks_right(
                    right=self.ctx.text(right_name(right))
                )
            case BotLacksRight(right=right):
                line = phrases.bot_lacks_right(right=self.ctx.text(right_name(right)))
            case TermOutOfRange(min_seconds=shortest, max_seconds=longest):
                line = phrases.term_out_of_range(
                    min=self.duration(shortest), max=self.duration(longest)
                )
            case _:
                raise exc
        await self.ctx.say(line, reply=True)
