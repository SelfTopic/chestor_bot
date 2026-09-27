from selfrot import CommandArgs, MessageHandler
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import GhoulNotFound, KaguneNotOwned, LastKaguneType

from ....context import AppContext
from ...targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ...types import ReplyUserMessage, TextMessage
from .catalog import TYPE_BY_NAME, TYPE_NAMES


async def _perform_remove(
    ctx: AppContext[Message], telegram_id: int, type_name: str
) -> None:
    phrases = Dialogs.admin.kagune
    kagune_type = TYPE_BY_NAME.get(type_name)
    if kagune_type is None:
        await ctx.say(phrases.unknown_type(types=TYPE_NAMES))
        return

    name = kagune_type.value["name"]
    error: Line | None = None
    try:
        await ctx.ghoul_service.revoke_kagune_type(telegram_id, kagune_type)
    except GhoulNotFound:
        error = Dialogs.admin.ghoul_not_found()
    except KaguneNotOwned:
        error = Dialogs.admin.kagune_not_owned(kagune=name)
    except LastKaguneType:
        error = Dialogs.admin.last_kagune()

    await ctx.say(error or phrases.removed(kagune=name))


class RemoveKaguneRepliedArgs(CommandArgs):
    type_name: str


class RemoveKaguneRepliedHandler(
    RepliedTargetHandler[RemoveKaguneRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("remove_kagune", RemoveKaguneRepliedArgs)
    query = cmd & HasReplyUser()
    usage = Dialogs.admin.kagune.remove_replied_usage(types=TYPE_NAMES)

    async def perform(self, telegram_id: int, args: RemoveKaguneRepliedArgs) -> None:
        await _perform_remove(self.ctx, telegram_id, args.type_name.lower())


class RemoveKaguneArgs(TargetArgs):
    type_name: str


class RemoveKaguneHandler(
    ExplicitTargetHandler[RemoveKaguneArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("remove_kagune", RemoveKaguneArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.kagune.remove_usage(types=TYPE_NAMES)

    async def perform(self, telegram_id: int, args: RemoveKaguneArgs) -> None:
        await _perform_remove(self.ctx, telegram_id, args.type_name.lower())
