from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.exceptions import GhoulNotFound

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage


class KillGhoulRepliedArgs(CommandArgs):
    cause: Rest = ""


async def _perform_kill(ctx: AppContext[Message], telegram_id: int, cause: str) -> None:
    cause = cause or "admin"
    try:
        updated = await ctx.ghoul_service.apply_death(telegram_id, cause=cause)
    except GhoulNotFound:
        await ctx.message.answer(ctx.text(Dialogs.admin.ghoul_not_found()))
        return

    done = Dialogs.admin.kill.done(id=telegram_id, cause=cause, deaths=updated.deaths)
    await ctx.message.answer(ctx.text(done), parse_mode="HTML")


class KillGhoulRepliedHandler(
    RepliedTargetHandler[KillGhoulRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("kill_ghoul", KillGhoulRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: KillGhoulRepliedArgs) -> None:
        await _perform_kill(self.ctx, telegram_id, args.cause)


class KillGhoulArgs(TargetArgs):
    cause: Rest = ""


class KillGhoulHandler(
    ExplicitTargetHandler[KillGhoulArgs],
    MessageHandler[AppContext[TextMessage]],
):
    cmd = Command("kill_ghoul", KillGhoulArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.kill.usage()

    async def perform(self, telegram_id: int, args: KillGhoulArgs) -> None:
        await _perform_kill(self.ctx, telegram_id, args.cause)


class KillRouter(BaseRouter[AppContext]):
    handlers = (KillGhoulRepliedHandler, KillGhoulHandler)
