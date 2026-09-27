from selfrot import BaseRouter, CommandArgs, MessageHandler
from selfrot.filter import Command, HasReplyUser, HasUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.exceptions import GhoulNotFound, UnknownStatField, UserNotFound
from src.bot.services.admin.stats_edit import (
    ALLOWED_GHOUL_FIELDS,
    ALLOWED_GHOUL_TIME_FIELDS,
    ALLOWED_USER_FIELDS,
)

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import TextUserMessage, TextUserReplyMessage

USAGE = Dialogs.admin.stats.usage(
    user_fields=", ".join(sorted(ALLOWED_USER_FIELDS)),
    ghoul_fields=", ".join(sorted(ALLOWED_GHOUL_FIELDS)),
    time_fields=", ".join(sorted(ALLOWED_GHOUL_TIME_FIELDS)),
)


async def _perform_set_stat(
    ctx: AppContext[Message], target: str, field: str, value: int, admin_id: int
) -> None:
    stats = Dialogs.admin.stats
    try:
        result = await ctx.stats_edit_service.set_stat(
            target, field, value, admin_id=admin_id
        )
    except UserNotFound as e:
        await ctx.message.answer(ctx.text(Dialogs.errors.user_not_found(query=e.query)))
        return
    except UnknownStatField as e:
        await ctx.message.answer(ctx.text(stats.unknown_field(field=e.field)))
        return
    except GhoulNotFound:
        await ctx.message.answer(ctx.text(stats.no_ghoul()))
        return

    target_label = (
        stats.target_ghoul() if result.is_ghoul_field else stats.target_user()
    )
    done = stats.done(
        field=result.field, target=ctx.text(target_label), value=result.value
    )
    await ctx.message.answer(ctx.text(done), parse_mode="HTML")


class SetStatRepliedArgs(CommandArgs):
    field: str
    value: int


class SetStatRepliedHandler(
    RepliedTargetHandler[SetStatRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = Command("set_stat", SetStatRepliedArgs)
    query = cmd & HasUser() & HasReplyUser()
    usage = USAGE

    async def perform(self, telegram_id: int, args: SetStatRepliedArgs) -> None:
        await _perform_set_stat(
            self.ctx, str(telegram_id), args.field, args.value, self.ctx.message.user.id
        )


class SetStatArgs(TargetArgs):
    field: str
    value: int


class SetStatHandler(
    ExplicitTargetHandler[SetStatArgs], MessageHandler[AppContext[TextUserMessage]]
):
    cmd = Command("set_stat", SetStatArgs)
    query = cmd & HasUser() & ~HasReplyUser()
    usage = USAGE

    async def perform(self, telegram_id: int, args: SetStatArgs) -> None:
        await _perform_set_stat(
            self.ctx, str(telegram_id), args.field, args.value, self.ctx.message.user.id
        )


class StatsEditRouter(BaseRouter[AppContext]):
    handlers = (SetStatRepliedHandler, SetStatHandler)
