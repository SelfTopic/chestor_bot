from selfrot import CommandArgs, MessageHandler
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from ....context import AppContext
from ....targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ....types import ReplyUserMessage, TextMessage
from .catalog import TYPE_BY_NAME, TYPE_NAMES


async def _perform_remove(
    ctx: AppContext[Message], telegram_id: int, type_name: str
) -> None:
    kagune_type = TYPE_BY_NAME.get(type_name)
    if kagune_type is None:
        await ctx.message.answer(f"❌ Неизвестный тип. Доступны: {TYPE_NAMES}.")
        return

    try:
        await ctx.ghoul_service.revoke_kagune_type(telegram_id, kagune_type)
    except ValueError as e:
        await ctx.message.answer(f"❌ {e}")
        return

    await ctx.message.answer(f"✅ Тип {kagune_type.value['name']} убран.")


class RemoveKaguneRepliedArgs(CommandArgs):
    type_name: str


class RemoveKaguneRepliedHandler(
    RepliedTargetHandler[RemoveKaguneRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("remove_kagune", RemoveKaguneRepliedArgs)
    query = cmd & HasReplyUser()
    usage = f"Использование (реплаем): /remove_kagune <{TYPE_NAMES}>"

    async def perform(self, telegram_id: int, args: RemoveKaguneRepliedArgs) -> None:
        await _perform_remove(self.ctx, telegram_id, args.type_name.lower())


class RemoveKaguneArgs(TargetArgs):
    type_name: str


class RemoveKaguneHandler(
    ExplicitTargetHandler[RemoveKaguneArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("remove_kagune", RemoveKaguneArgs)
    query = cmd & ~HasReplyUser()
    usage = f"Использование: /remove_kagune <id или @username> <{TYPE_NAMES}>"

    async def perform(self, telegram_id: int, args: RemoveKaguneArgs) -> None:
        await _perform_remove(self.ctx, telegram_id, args.type_name.lower())
