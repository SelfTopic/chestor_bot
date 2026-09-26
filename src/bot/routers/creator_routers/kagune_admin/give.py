from selfrot import CommandArgs, MessageHandler
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from ....context import AppContext
from ...targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ...types import ReplyUserMessage, TextMessage
from .catalog import TYPE_BY_NAME, TYPE_NAMES


async def _perform_give(
    ctx: AppContext[Message], telegram_id: int, type_name: str
) -> None:
    ghoul_service = ctx.ghoul_service

    try:
        if type_name == "all":
            ghoul = await ghoul_service.grant_all_kagune_types(telegram_id)
            names = ", ".join(
                kt.value["name"] for kt in ghoul_service.owned_kagune_types(ghoul)
            )
            await ctx.message.answer(f"✅ Выданы все типы кагуне. Открыто: {names}.")
            return

        kagune_type = TYPE_BY_NAME.get(type_name)
        if kagune_type is None:
            await ctx.message.answer(
                f"❌ Неизвестный тип. Доступны: {TYPE_NAMES}, all."
            )
            return

        ghoul = await ghoul_service.grant_kagune_type(telegram_id, kagune_type)
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        await ctx.message.answer(
            f"✅ Выдан тип {kagune_type.value['name']} (сила {strength})."
        )
    except ValueError as e:
        await ctx.message.answer(f"❌ {e}")


class GiveKaguneRepliedArgs(CommandArgs):
    type_name: str


class GiveKaguneRepliedHandler(
    RepliedTargetHandler[GiveKaguneRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("give_kagune", GiveKaguneRepliedArgs)
    query = cmd & HasReplyUser()
    usage = f"Использование (реплаем): /give_kagune <{TYPE_NAMES}|all>"

    async def perform(self, telegram_id: int, args: GiveKaguneRepliedArgs) -> None:
        await _perform_give(self.ctx, telegram_id, args.type_name.lower())


class GiveKaguneArgs(TargetArgs):
    type_name: str


class GiveKaguneHandler(
    ExplicitTargetHandler[GiveKaguneArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("give_kagune", GiveKaguneArgs)
    query = cmd & ~HasReplyUser()
    usage = f"Использование: /give_kagune <id или @username> <{TYPE_NAMES}|all>"

    async def perform(self, telegram_id: int, args: GiveKaguneArgs) -> None:
        await _perform_give(self.ctx, telegram_id, args.type_name.lower())
