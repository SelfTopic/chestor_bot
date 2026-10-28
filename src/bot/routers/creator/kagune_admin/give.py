from selfrot import CommandArgs
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.dialogs.vocab import KAGUNE_NAMES
from src.bot.exceptions import GhoulNotFound, KaguneAlreadyOwned

from ....context import AppContext
from ...targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ...types import ReplyUserMessage, TextMessage
from .catalog import TYPE_BY_NAME, TYPE_NAMES


async def _perform_give(
    ctx: AppContext[Message], telegram_id: int, type_name: str
) -> None:
    ghoul_service = ctx.ghoul_service
    phrases = Dialogs.admin.kagune

    try:
        if type_name == "all":
            ghoul = await ghoul_service.grant_all_kagune_types(telegram_id)
            names = ", ".join(
                ctx.text(KAGUNE_NAMES[kt]) for kt in ghoul_service.owned_kagune_types(ghoul)
            )
            await ctx.say(phrases.all_given(names=names))
            return

        kagune_type = TYPE_BY_NAME.get(type_name)
        if kagune_type is None:
            unknown = phrases.unknown_type_or_all(types=TYPE_NAMES)
            await ctx.say(unknown)
            return

        ghoul = await ghoul_service.grant_kagune_type(telegram_id, kagune_type)
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        given = phrases.given(kagune=KAGUNE_NAMES[kagune_type], strength=strength)
        await ctx.say(given)
    except GhoulNotFound:
        await ctx.say(Dialogs.admin.ghoul_not_found())
    except KaguneAlreadyOwned as e:
        owned = Dialogs.admin.kagune_already_owned(kagune=KAGUNE_NAMES[e.kagune_type])
        await ctx.say(owned)


class GiveKaguneRepliedArgs(CommandArgs):
    type_name: str


class GiveKaguneRepliedHandler(
    RepliedTargetHandler[GiveKaguneRepliedArgs, AppContext[ReplyUserMessage]],
):
    cmd = Command("give_kagune", GiveKaguneRepliedArgs)
    query = cmd & HasReplyUser()
    usage = Dialogs.admin.kagune.give_replied_usage(types=TYPE_NAMES)

    async def perform(self, telegram_id: int, args: GiveKaguneRepliedArgs) -> None:
        await _perform_give(self.ctx, telegram_id, args.type_name.lower())


class GiveKaguneArgs(TargetArgs):
    type_name: str


class GiveKaguneHandler(ExplicitTargetHandler[GiveKaguneArgs, AppContext[TextMessage]]):
    cmd = Command("give_kagune", GiveKaguneArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.kagune.give_usage(types=TYPE_NAMES)

    async def perform(self, telegram_id: int, args: GiveKaguneArgs) -> None:
        await _perform_give(self.ctx, telegram_id, args.type_name.lower())
