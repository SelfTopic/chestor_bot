from selfrot import CommandArgs, MessageHandler
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from src.bot.dialogs import Dialogs
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
                kt.value["name"] for kt in ghoul_service.owned_kagune_types(ghoul)
            )
            await ctx.message.answer(ctx.text(phrases.all_given(names=names)))
            return

        kagune_type = TYPE_BY_NAME.get(type_name)
        if kagune_type is None:
            unknown = phrases.unknown_type_or_all(types=TYPE_NAMES)
            await ctx.message.answer(ctx.text(unknown))
            return

        ghoul = await ghoul_service.grant_kagune_type(telegram_id, kagune_type)
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        given = phrases.given(kagune=kagune_type.value["name"], strength=strength)
        await ctx.message.answer(ctx.text(given))
    except GhoulNotFound:
        await ctx.message.answer(ctx.text(Dialogs.admin.ghoul_not_found()))
    except KaguneAlreadyOwned as e:
        owned = Dialogs.admin.kagune_already_owned(kagune=e.kagune_type.value["name"])
        await ctx.message.answer(ctx.text(owned))


class GiveKaguneRepliedArgs(CommandArgs):
    type_name: str


class GiveKaguneRepliedHandler(
    RepliedTargetHandler[GiveKaguneRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("give_kagune", GiveKaguneRepliedArgs)
    query = cmd & HasReplyUser()
    usage = Dialogs.admin.kagune.give_replied_usage(types=TYPE_NAMES)

    async def perform(self, telegram_id: int, args: GiveKaguneRepliedArgs) -> None:
        await _perform_give(self.ctx, telegram_id, args.type_name.lower())


class GiveKaguneArgs(TargetArgs):
    type_name: str


class GiveKaguneHandler(
    ExplicitTargetHandler[GiveKaguneArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("give_kagune", GiveKaguneArgs)
    query = cmd & ~HasReplyUser()
    usage = Dialogs.admin.kagune.give_usage(types=TYPE_NAMES)

    async def perform(self, telegram_id: int, args: GiveKaguneArgs) -> None:
        await _perform_give(self.ctx, telegram_id, args.type_name.lower())
