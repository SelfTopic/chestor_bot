from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import HasReplyUser, HasUser
from selfrot.types import ChatMemberBanned

from src.bot.dialogs import Line
from src.bot.exceptions import TargetNotBanned
from src.bot.types import ModerationActionType

from ....context import AppContext
from ...targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ...types import TextUserMessage, TextUserReplyMessage
from ..filters import FromChatAdmin
from ..flow import command
from .flow import PunishmentFlow


class BanFlow(PunishmentFlow):
    def voiced_usage(self) -> Line:
        return self.phrases.ban_usage()

    async def ban(self, telegram_id: int, text: str) -> None:
        moderator_id = await self.check_rights()
        punishment = self.ctx.moderation_service.punishment(
            text, self.settings.ban_default_seconds
        )
        member = await self.punishable(telegram_id)

        chat_id = self.ctx.message.chat.id
        await self.ctx.bot.ban_chat_member(
            chat_id, telegram_id, until_date=self.until_date(punishment.seconds)
        )
        await self.ctx.moderation_service.record(
            chat_id,
            moderator_id,
            telegram_id,
            ModerationActionType.BAN,
            duration_seconds=punishment.seconds,
            reason=punishment.reason,
        )

        name = member.user.first_name
        term = self.term(punishment.seconds)
        if punishment.reason is None:
            line = self.phrases.banned(name=name, term=term)
        else:
            line = self.phrases.banned_for(
                name=name, term=term, reason=punishment.reason
            )
        await self.ctx.say(line, reply=True)


class BanRepliedArgs(CommandArgs):
    rest: Rest = ""


class BanRepliedHandler(
    BanFlow,
    RepliedTargetHandler[BanRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = command("ban", "бан", BanRepliedArgs)
    query = cmd & HasUser() & HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: BanRepliedArgs) -> None:
        await self.ban(telegram_id, args.rest)


class BanArgs(TargetArgs):
    rest: Rest = ""


class BanHandler(
    BanFlow,
    ExplicitTargetHandler[BanArgs],
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("ban", "бан", BanArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: BanArgs) -> None:
        await self.ban(telegram_id, args.rest)


class UnbanFlow(PunishmentFlow):
    def voiced_usage(self) -> Line:
        return self.phrases.unban_usage()

    async def unban(self, telegram_id: int) -> None:
        moderator_id = await self.check_rights()
        member = await self.target_member(telegram_id)
        name = member.user.first_name
        if not isinstance(member, ChatMemberBanned):
            raise TargetNotBanned(name)

        chat_id = self.ctx.message.chat.id
        await self.ctx.bot.unban_chat_member(chat_id, telegram_id, only_if_banned=True)
        await self.ctx.moderation_service.record(
            chat_id, moderator_id, telegram_id, ModerationActionType.UNBAN
        )
        await self.ctx.say(self.phrases.unbanned(name=name), reply=True)


class UnbanRepliedArgs(CommandArgs):
    note: Rest = ""


class UnbanRepliedHandler(
    UnbanFlow,
    RepliedTargetHandler[UnbanRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = command("unban", "разбан", UnbanRepliedArgs)
    query = cmd & HasUser() & HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: UnbanRepliedArgs) -> None:
        await self.unban(telegram_id)


class UnbanArgs(TargetArgs):
    pass


class UnbanHandler(
    UnbanFlow,
    ExplicitTargetHandler[UnbanArgs],
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("unban", "разбан", UnbanArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: UnbanArgs) -> None:
        await self.unban(telegram_id)
