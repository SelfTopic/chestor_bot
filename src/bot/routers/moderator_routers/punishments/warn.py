from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import HasReplyUser, HasUser

from src.bot.dialogs import Line
from src.bot.exceptions import TargetHasNoWarnings
from src.bot.types import ModerationActionType, WarnOutcome, WarnPenalty

from ....context import AppContext
from ...targeting import RepliedTargetHandler
from ...types import TextUserMessage, TextUserReplyMessage
from ..filters import FromChatAdmin
from .targets import AnywhereTargetHandler, TargetTextArgs
from ..flow import command
from .flow import PunishmentFlow, is_absent

PENALTY_ACTIONS = {
    WarnPenalty.MUTE: ModerationActionType.MUTE,
    WarnPenalty.BAN: ModerationActionType.BAN,
    WarnPenalty.KICK: ModerationActionType.KICK,
}


class WarnFlow(PunishmentFlow):
    def voiced_usage(self) -> Line:
        return self.phrases.warn_usage()

    async def warn(self, telegram_id: int, text: str) -> None:
        moderator_id = await self.check_rights()
        member = await self.punishable(telegram_id)
        reason = text.strip() or None
        outcome = await self.ctx.moderation_service.warn(
            self.settings, moderator_id, telegram_id, reason
        )

        name = member.user.first_name
        who = dict(chat=self.chat_title, moderator=self.moderator_name, id=telegram_id)
        counts = dict(count=outcome.count, limit=outcome.limit)
        if reason is None:
            line = self.phrases.warned(name=name, **counts)
            log = self.phrases.log_warned(name=name, **counts, **who)
        else:
            line = self.phrases.warned_for(name=name, reason=reason, **counts)
            log = self.phrases.log_warned_for(name=name, reason=reason, **counts, **who)
        self.report(log)

        if outcome.penalty is None:
            await self.ctx.say(line, reply=True)
            return

        # Кик того, кого уже нет в чате, снял бы с него бан: такого только обнуляем.
        if outcome.penalty is WarnPenalty.KICK and is_absent(member):
            await self.ctx.say(line, reply=True)
            return

        await self.punish(telegram_id, outcome, moderator_id, reason)
        await self.ctx.say(self.penalty_line(name, outcome), reply=True)
        self.report(self.penalty_log(name, telegram_id, outcome))

    async def punish(
        self,
        telegram_id: int,
        outcome: WarnOutcome,
        moderator_id: int,
        reason: str | None,
    ) -> None:
        match outcome.penalty:
            case WarnPenalty.MUTE:
                await self.restrict(telegram_id, outcome.penalty_seconds)
            case WarnPenalty.BAN:
                await self.ban_member(telegram_id, outcome.penalty_seconds)
            case WarnPenalty.KICK:
                await self.kick_member(telegram_id)
            case None:
                return

        await self.ctx.moderation_service.record(
            self.ctx.message.chat.id,
            moderator_id,
            telegram_id,
            PENALTY_ACTIONS[outcome.penalty],
            duration_seconds=outcome.penalty_seconds,
            reason=reason,
        )

    def penalty_line(self, name: str, outcome: WarnOutcome) -> Line:
        term = self.term(outcome.penalty_seconds)
        match outcome.penalty:
            case WarnPenalty.MUTE:
                return self.phrases.warn_penalty_muted(name=name, limit=outcome.limit, term=term)
            case WarnPenalty.BAN:
                return self.phrases.warn_penalty_banned(
                    name=name, limit=outcome.limit, term=term
                )
            case _:
                return self.phrases.warn_penalty_kicked(name=name, limit=outcome.limit)

    def penalty_log(self, name: str, telegram_id: int, outcome: WarnOutcome) -> Line:
        term = self.term(outcome.penalty_seconds)
        who = dict(
            chat=self.chat_title,
            moderator=self.moderator_name,
            id=telegram_id,
            name=name,
            limit=outcome.limit,
        )
        match outcome.penalty:
            case WarnPenalty.MUTE:
                return self.phrases.log_warn_penalty_muted(term=term, **who)
            case WarnPenalty.BAN:
                return self.phrases.log_warn_penalty_banned(term=term, **who)
            case _:
                return self.phrases.log_warn_penalty_kicked(**who)


WARN_WORDS = ("варн", "пред")


class WarnRepliedArgs(CommandArgs):
    reason: Rest = ""


class WarnRepliedHandler(
    WarnFlow,
    RepliedTargetHandler[WarnRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = command("warn", WARN_WORDS, WarnRepliedArgs)
    query = cmd & HasUser() & HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: WarnRepliedArgs) -> None:
        await self.warn(telegram_id, args.reason)


class WarnHandler(
    WarnFlow,
    AnywhereTargetHandler,
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("warn", WARN_WORDS, TargetTextArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, rest: str) -> None:
        await self.warn(telegram_id, rest)


class UnwarnFlow(PunishmentFlow):
    def voiced_usage(self) -> Line:
        return self.phrases.unwarn_usage()

    async def unwarn(self, telegram_id: int) -> None:
        moderator_id = await self.check_moderator()
        member = await self.target_member(telegram_id)
        name = member.user.first_name
        chat_id = self.ctx.message.chat.id
        left = await self.ctx.moderation_service.unwarn(chat_id, moderator_id, telegram_id)
        if left is None:
            raise TargetHasNoWarnings(name)

        counts = dict(count=left, limit=self.settings.warn_limit)
        await self.ctx.say(self.phrases.unwarned(name=name, **counts), reply=True)
        self.report(
            self.phrases.log_unwarned(
                chat=self.chat_title,
                moderator=self.moderator_name,
                name=name,
                id=telegram_id,
                **counts,
            )
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, TargetHasNoWarnings):
            await self.ctx.say(self.phrases.no_warnings(name=exc.name), reply=True)
            return

        await super().on_error(exc)


UNWARN_WORDS = ("снять варн", "снять пред")


class UnwarnRepliedArgs(CommandArgs):
    note: Rest = ""


class UnwarnRepliedHandler(
    UnwarnFlow,
    RepliedTargetHandler[UnwarnRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = command("unwarn", UNWARN_WORDS, UnwarnRepliedArgs)
    query = cmd & HasUser() & HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: UnwarnRepliedArgs) -> None:
        await self.unwarn(telegram_id)


class UnwarnHandler(
    UnwarnFlow,
    AnywhereTargetHandler,
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("unwarn", UNWARN_WORDS, TargetTextArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, rest: str) -> None:
        await self.unwarn(telegram_id)
