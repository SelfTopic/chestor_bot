from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import HasReplyUser, HasUser
from selfrot.types import ChatMemberRestricted, ChatPermissions

from src.bot.dialogs import Line
from src.bot.exceptions import TargetNotMuted
from src.bot.types import ModerationActionType, ModerationFeature

from ....context import AppContext
from ...targeting import RepliedTargetHandler
from ...types import TextUserMessage, TextUserReplyMessage
from ..filters import FromChatAdmin
from .targets import AnywhereTargetHandler, TargetTextArgs
from ..flow import command
from .flow import PunishmentFlow

# Все права True — так Bot API снимает ограничения целиком.
UNMUTED = ChatPermissions(**dict.fromkeys(ChatPermissions.model_fields, True))


class MuteFlow(PunishmentFlow):
    def voiced_usage(self) -> Line:
        return self.phrases.mute_usage()

    async def mute(self, telegram_id: int, text: str) -> None:
        self.require(ModerationFeature.MUTE)
        moderator_id = await self.check_rights()
        punishment = self.ctx.moderation_service.punishment(
            text, self.settings.mute_default_seconds
        )
        member = await self.punishable(telegram_id)

        await self.restrict(telegram_id, punishment.seconds)
        await self.ctx.moderation_service.record(
            self.ctx.message.chat.id,
            moderator_id,
            telegram_id,
            ModerationActionType.MUTE,
            duration_seconds=punishment.seconds,
            reason=punishment.reason,
        )

        name = member.user.first_name
        term = self.term(punishment.seconds)
        who = dict(chat=self.chat_title, moderator=self.moderator_name, id=telegram_id)
        if punishment.reason is None:
            line = self.phrases.muted(name=name, term=term)
            log = self.phrases.log_muted(name=name, term=term, **who)
        else:
            line = self.phrases.muted_for(
                name=name, term=term, reason=punishment.reason
            )
            log = self.phrases.log_muted_for(
                name=name, term=term, reason=punishment.reason, **who
            )
        await self.ctx.say(line, reply=True)
        self.report(log)


class MuteRepliedArgs(CommandArgs):
    rest: Rest = ""


class MuteRepliedHandler(
    MuteFlow,
    RepliedTargetHandler[MuteRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = command("mute", "мут", MuteRepliedArgs)
    query = cmd & HasUser() & HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: MuteRepliedArgs) -> None:
        await self.mute(telegram_id, args.rest)


class MuteHandler(
    MuteFlow,
    AnywhereTargetHandler,
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("mute", "мут", TargetTextArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, rest: str) -> None:
        await self.mute(telegram_id, rest)


class UnmuteFlow(PunishmentFlow):
    def voiced_usage(self) -> Line:
        return self.phrases.unmute_usage()

    async def unmute(self, telegram_id: int) -> None:
        self.require(ModerationFeature.MUTE)
        moderator_id = await self.check_rights()
        member = await self.target_member(telegram_id)
        name = member.user.first_name
        if not isinstance(member, ChatMemberRestricted) or member.can_send_messages:
            raise TargetNotMuted(name)

        chat_id = self.ctx.message.chat.id
        await self.ctx.bot.restrict_chat_member(chat_id, telegram_id, UNMUTED)
        await self.ctx.moderation_service.record(
            chat_id, moderator_id, telegram_id, ModerationActionType.UNMUTE
        )
        await self.ctx.say(self.phrases.unmuted(name=name), reply=True)
        self.report(
            self.phrases.log_unmuted(
                chat=self.chat_title,
                moderator=self.moderator_name,
                name=name,
                id=telegram_id,
            )
        )


class UnmuteRepliedArgs(CommandArgs):
    note: Rest = ""


class UnmuteRepliedHandler(
    UnmuteFlow,
    RepliedTargetHandler[UnmuteRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = command("unmute", "размут", UnmuteRepliedArgs)
    query = cmd & HasUser() & HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: UnmuteRepliedArgs) -> None:
        await self.unmute(telegram_id)


class UnmuteHandler(
    UnmuteFlow,
    AnywhereTargetHandler,
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("unmute", "размут", TargetTextArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, rest: str) -> None:
        await self.unmute(telegram_id)
