from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import HasReplyUser, HasUser

from src.bot.dialogs import Line
from src.bot.exceptions import TargetAbsent
from src.bot.types import ModerationActionType, ModerationFeature

from ....context import AppContext
from ...targeting import RepliedTargetHandler
from ...types import TextUserMessage, TextUserReplyMessage
from ..filters import FromChatAdmin
from .targets import AnywhereTargetHandler, TargetTextArgs
from ..flow import command
from .flow import PunishmentFlow, is_absent


class KickFlow(PunishmentFlow):
    def voiced_usage(self) -> Line:
        return self.phrases.kick_usage()

    async def kick(self, telegram_id: int, text: str) -> None:
        self.require(ModerationFeature.KICK)
        moderator_id = await self.check_rights()
        member = await self.punishable(telegram_id)
        name = member.user.first_name
        # Разбан после бана вернул бы забаненному вход, поэтому отсутствующих не трогаем.
        if is_absent(member):
            raise TargetAbsent(name)

        await self.kick_member(telegram_id)
        reason = text.strip() or None
        await self.ctx.moderation_service.record(
            self.ctx.message.chat.id, moderator_id, telegram_id, ModerationActionType.KICK, reason=reason
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


class KickHandler(
    KickFlow,
    AnywhereTargetHandler,
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("kick", "кик", TargetTextArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, rest: str) -> None:
        await self.kick(telegram_id, rest)
