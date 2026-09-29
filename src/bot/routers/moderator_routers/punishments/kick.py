from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import HasReplyUser, HasUser
from selfrot.types import ChatMemberBanned, ChatMemberLeft, ChatMemberRestricted

from src.bot.dialogs import Line
from src.bot.exceptions import TargetAbsent
from src.bot.types import ModerationActionType

from ....context import AppContext
from ...targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ...types import TextUserMessage, TextUserReplyMessage
from ..filters import FromChatAdmin
from ..flow import command
from .flow import PunishmentFlow


class KickFlow(PunishmentFlow):
    def voiced_usage(self) -> Line:
        return self.phrases.kick_usage()

    async def kick(self, telegram_id: int, text: str) -> None:
        moderator_id = await self.check_rights()
        member = await self.punishable(telegram_id)
        name = member.user.first_name
        # Разбан после бана вернул бы забаненному вход, поэтому отсутствующих не трогаем.
        if isinstance(member, (ChatMemberLeft, ChatMemberBanned)) or (
            isinstance(member, ChatMemberRestricted) and not member.is_member
        ):
            raise TargetAbsent(name)

        chat_id = self.ctx.message.chat.id
        await self.ctx.bot.ban_chat_member(chat_id, telegram_id)
        await self.ctx.bot.unban_chat_member(chat_id, telegram_id, only_if_banned=True)
        reason = text.strip() or None
        await self.ctx.moderation_service.record(
            chat_id, moderator_id, telegram_id, ModerationActionType.KICK, reason=reason
        )

        who = dict(chat=self.chat_title, moderator=self.moderator_name, id=telegram_id)
        if reason is None:
            line = self.phrases.kicked(name=name)
            log = self.phrases.log_kicked(name=name, **who)
        else:
            line = self.phrases.kicked_for(name=name, reason=reason)
            log = self.phrases.log_kicked_for(name=name, reason=reason, **who)
        await self.ctx.say(line, reply=True)
        self.report(log)


class KickRepliedArgs(CommandArgs):
    reason: Rest = ""


class KickRepliedHandler(
    KickFlow,
    RepliedTargetHandler[KickRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = command("kick", "кик", KickRepliedArgs)
    query = cmd & HasUser() & HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: KickRepliedArgs) -> None:
        await self.kick(telegram_id, args.reason)


class KickArgs(TargetArgs):
    reason: Rest = ""


class KickHandler(
    KickFlow,
    ExplicitTargetHandler[KickArgs],
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("kick", "кик", KickArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: KickArgs) -> None:
        await self.kick(telegram_id, args.reason)
