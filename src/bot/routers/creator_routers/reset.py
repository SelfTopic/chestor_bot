from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.exceptions import UserNotFound

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage


class ResetRepliedArgs(CommandArgs):
    note: Rest = ""


async def _perform_reset_ghoul(ctx: AppContext[Message], target: str) -> None:
    try:
        result = await ctx.reset_service.reset_ghoul(target)
    except UserNotFound as e:
        await ctx.message.answer(ctx.text(Dialogs.errors.user_not_found(query=e.query)))
        return

    if not result.ghoul_deleted:
        await ctx.message.answer(ctx.text(Dialogs.admin.reset.no_ghoul()))
        return

    done = Dialogs.admin.reset.ghoul_done(id=result.telegram_id)
    await ctx.message.answer(ctx.text(done), parse_mode="HTML")


class ResetGhoulRepliedHandler(
    RepliedTargetHandler[ResetRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("reset_ghoul", ResetRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: ResetRepliedArgs) -> None:
        await _perform_reset_ghoul(self.ctx, str(telegram_id))


class ResetGhoulHandler(
    ExplicitTargetHandler[TargetArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("reset_ghoul", TargetArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.reset.ghoul_usage()

    async def perform(self, telegram_id: int, args: TargetArgs) -> None:
        await _perform_reset_ghoul(self.ctx, str(telegram_id))


async def _perform_reset_user(ctx: AppContext[Message], target: str) -> None:
    try:
        result = await ctx.reset_service.reset_user(target)
    except UserNotFound as e:
        await ctx.message.answer(ctx.text(Dialogs.errors.user_not_found(query=e.query)))
        return

    reset = Dialogs.admin.reset
    ghoul_deleted = (
        reset.ghoul_deleted() if result.ghoul_deleted else reset.ghoul_missing()
    )
    done = reset.user_done(id=result.telegram_id, ghoul_deleted=ctx.text(ghoul_deleted))
    await ctx.message.answer(ctx.text(done), parse_mode="HTML")


class ResetUserRepliedHandler(
    RepliedTargetHandler[ResetRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("reset_user", ResetRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: ResetRepliedArgs) -> None:
        await _perform_reset_user(self.ctx, str(telegram_id))


class ResetUserHandler(
    ExplicitTargetHandler[TargetArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("reset_user", TargetArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.reset.user_usage()

    async def perform(self, telegram_id: int, args: TargetArgs) -> None:
        await _perform_reset_user(self.ctx, str(telegram_id))


class ResetRouter(BaseRouter[AppContext]):
    handlers = (
        ResetGhoulRepliedHandler,
        ResetGhoulHandler,
        ResetUserRepliedHandler,
        ResetUserHandler,
    )
