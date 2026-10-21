from selfrot import BaseRouter, CommandArgs
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage


async def _set_service(ctx: AppContext[Message], telegram_id: int, value: bool) -> None:
    await ctx.user_service.set_service(telegram_id, value)
    line = (
        Dialogs.admin.service.marked(id=telegram_id)
        if value
        else Dialogs.admin.service.unmarked(id=telegram_id)
    )
    await ctx.say(line, parse_mode="HTML")


class MarkServiceRepliedHandler(RepliedTargetHandler[CommandArgs, AppContext[ReplyUserMessage]]):
    cmd = Command("mark_service", CommandArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: CommandArgs) -> None:
        await _set_service(self.ctx, telegram_id, True)


class MarkServiceHandler(ExplicitTargetHandler[TargetArgs, AppContext[TextMessage]]):
    cmd = Command("mark_service", TargetArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.service.usage()

    async def perform(self, telegram_id: int, args: TargetArgs) -> None:
        await _set_service(self.ctx, telegram_id, True)


class UnmarkServiceRepliedHandler(RepliedTargetHandler[CommandArgs, AppContext[ReplyUserMessage]]):
    cmd = Command("unmark_service", CommandArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: CommandArgs) -> None:
        await _set_service(self.ctx, telegram_id, False)


class UnmarkServiceHandler(ExplicitTargetHandler[TargetArgs, AppContext[TextMessage]]):
    cmd = Command("unmark_service", TargetArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.service.unmark_usage()

    async def perform(self, telegram_id: int, args: TargetArgs) -> None:
        await _set_service(self.ctx, telegram_id, False)


class ServiceFlagRouter(BaseRouter[AppContext]):
    handlers = (
        MarkServiceRepliedHandler,
        MarkServiceHandler,
        UnmarkServiceRepliedHandler,
        UnmarkServiceHandler,
    )
