from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage

USAGE = (
    "Использование: /ban <id или @username> [длительность] [причина]\n\n"
    "Длительность: 30m, 24h, 7d (без неё — перманентно)\n"
    "Примеры:\n"
    "/ban @username\n"
    "/ban 123456789 7d читерство\n"
    "/ban @username 24h флуд"
)


async def _perform_ban(
    ctx: AppContext[Message], target: str, duration: str, reason: str
) -> None:
    ban_service = ctx.ban_service

    try:
        user = await ban_service._resolve_user(target)  # noqa: SLF001
    except ValueError as e:
        await ctx.message.reply(f"❌ {e}")
        return

    if user.is_banned:
        await ctx.message.reply("⚠️ Пользователь уже забанен.")
        return

    result = await ban_service.ban(target, duration_str=duration, reason=reason)
    await ctx.message.reply(ban_service.format_ban_result(result), parse_mode="HTML")


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
    usage = USAGE

    async def perform(self, telegram_id: int, args: BanArgs) -> None:
        await _perform_ban(self.ctx, str(telegram_id), args.duration, args.reason)


async def _perform_unban(ctx: AppContext[Message], target: str) -> None:
    ban_service = ctx.ban_service

    try:
        user = await ban_service._resolve_user(target)  # noqa: SLF001
    except ValueError as e:
        await ctx.message.reply(f"❌ {e}")
        return

    if not user.is_banned:
        await ctx.message.reply("⚠️ Пользователь не забанен.")
        return

    unbanned = await ban_service.unban(target)
    await ctx.message.reply(
        f"✅ Пользователь <code>{unbanned.telegram_id}</code> ({unbanned.full_name}) разблокирован.",
        parse_mode="HTML",
    )


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
    usage = "Использование: /unban <id или @username>"

    async def perform(self, telegram_id: int, args: UnbanArgs) -> None:
        await _perform_unban(self.ctx, str(telegram_id))


class BanRouter(BaseRouter[AppContext]):
    handlers = (BanRepliedHandler, BanHandler, UnbanRepliedHandler, UnbanHandler)
