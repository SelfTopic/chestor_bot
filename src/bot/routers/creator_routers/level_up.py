from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.exceptions import GhoulNotFound

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage


def _flag(ctx: AppContext[Message], value: bool) -> str:
    return ctx.text(Dialogs.admin.flag_yes() if value else Dialogs.admin.flag_no())


async def _perform_level_up(ctx: AppContext[Message], telegram_id: int) -> None:
    try:
        result = await ctx.level_up_service.level_up(telegram_id)
    except GhoulNotFound:
        await ctx.message.answer(ctx.text(Dialogs.admin.ghoul_not_found()))
        return

    done = Dialogs.admin.level_up.done(
        level=result.ghoul.level,
        cheston=result.cheston_reward,
        rc=result.rc_reward,
        notified=_flag(ctx, result.notified),
    )
    await ctx.message.answer(ctx.text(done))


class ForceLevelupRepliedArgs(CommandArgs):
    note: Rest = ""


class ForceLevelupRepliedHandler(
    RepliedTargetHandler[ForceLevelupRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("force_levelup", ForceLevelupRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: ForceLevelupRepliedArgs) -> None:
        await _perform_level_up(self.ctx, telegram_id)


class ForceLevelupHandler(
    ExplicitTargetHandler[TargetArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("force_levelup", TargetArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.level_up.usage()

    async def perform(self, telegram_id: int, args: TargetArgs) -> None:
        await _perform_level_up(self.ctx, telegram_id)


async def _perform_add_progress(
    ctx: AppContext[Message], telegram_id: int, delta: float
) -> None:
    progress = Dialogs.admin.progress
    if not -100 <= delta <= 100:
        await ctx.message.answer(ctx.text(progress.delta_range()))
        return

    try:
        result = await ctx.level_up_service.add_progress(telegram_id, delta)
    except GhoulNotFound:
        await ctx.message.answer(ctx.text(Dialogs.admin.ghoul_not_found()))
        return

    lines = [
        progress.done(progress=f"{result.progress:.2f}", levels=result.levels_gained)
    ]
    lines += [
        progress.level(
            level=level.ghoul.level,
            cheston=level.cheston_reward,
            rc=level.rc_reward,
            notified=_flag(ctx, level.notified),
        )
        for level in result.level_up_results
    ]

    await ctx.message.answer("\n".join(ctx.text(line) for line in lines))


class AddProgressRepliedArgs(CommandArgs):
    delta: float


class AddProgressRepliedHandler(
    RepliedTargetHandler[AddProgressRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("add_progress", AddProgressRepliedArgs)
    query = cmd & HasReplyUser()
    usage = Dialogs.admin.progress.replied_usage()

    async def perform(self, telegram_id: int, args: AddProgressRepliedArgs) -> None:
        await _perform_add_progress(self.ctx, telegram_id, args.delta)


class AddProgressArgs(TargetArgs):
    delta: float


class AddProgressHandler(
    ExplicitTargetHandler[AddProgressArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("add_progress", AddProgressArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.progress.usage()

    async def perform(self, telegram_id: int, args: AddProgressArgs) -> None:
        await _perform_add_progress(self.ctx, telegram_id, args.delta)


class LevelUpRouter(BaseRouter[AppContext]):
    handlers = (
        ForceLevelupRepliedHandler,
        ForceLevelupHandler,
        AddProgressRepliedHandler,
        AddProgressHandler,
    )
