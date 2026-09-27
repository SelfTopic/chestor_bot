from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.exceptions import UserNotFound

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage
from .ban_term import ban_term


async def _perform_ban(
    ctx: AppContext[Message], target: str, duration: str, reason: str
) -> None:
    ban_service = ctx.ban_service

    try:
        user = await ban_service._resolve_user(target)  # noqa: SLF001
    except UserNotFound as e:
        await ctx.say(Dialogs.errors.user_not_found(query=e.query), reply=True)
        return

    if user.is_banned:
        await ctx.say(Dialogs.admin.ban.already(), reply=True)
        return

    result = await ban_service.ban(target, duration_str=duration, reason=reason)
    done = Dialogs.admin.ban.done(
        id=result.user.telegram_id,
        name=result.user.full_name,
        term=ban_term(ctx, result.banned_until),
        reason=result.reason or "—",
    )
    await ctx.say(done, reply=True, parse_mode="HTML")


class BanRepliedArgs(CommandArgs):
    duration: str = ""
    reason: Rest = ""


class BanRepliedHandler(
    RepliedTargetHandler[BanRepliedArgs], MessageHandler[AppContext[ReplyUserMessage]]
):
    cmd = Command("ban_bot", BanRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: BanRepliedArgs) -> None:
        await _perform_ban(self.ctx, str(telegram_id), args.duration, args.reason)


class BanArgs(TargetArgs):
    duration: str = ""
    reason: Rest = ""


class BanHandler(
    ExplicitTargetHandler[BanArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("ban_bot", BanArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.ban.usage()

    async def perform(self, telegram_id: int, args: BanArgs) -> None:
        await _perform_ban(self.ctx, str(telegram_id), args.duration, args.reason)


async def _perform_unban(ctx: AppContext[Message], target: str) -> None:
    ban_service = ctx.ban_service

    try:
        user = await ban_service._resolve_user(target)  # noqa: SLF001
    except UserNotFound as e:
        await ctx.say(Dialogs.errors.user_not_found(query=e.query), reply=True)
        return

    if not user.is_banned:
        await ctx.say(Dialogs.admin.unban.not_banned(), reply=True)
        return

    unbanned = await ban_service.unban(target)
    done = Dialogs.admin.unban.done(id=unbanned.telegram_id, name=unbanned.full_name)
    await ctx.say(done, reply=True, parse_mode="HTML")


class UnbanRepliedArgs(CommandArgs):
    note: Rest = ""


class UnbanRepliedHandler(
    RepliedTargetHandler[UnbanRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("unban", UnbanRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: UnbanRepliedArgs) -> None:
        await _perform_unban(self.ctx, str(telegram_id))


class UnbanArgs(TargetArgs):
    pass


class UnbanHandler(
    ExplicitTargetHandler[UnbanArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("unban", UnbanArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.unban.usage()

    async def perform(self, telegram_id: int, args: UnbanArgs) -> None:
        await _perform_unban(self.ctx, str(telegram_id))


class BanRouter(BaseRouter[AppContext]):
    handlers = (BanRepliedHandler, BanHandler, UnbanRepliedHandler, UnbanHandler)
