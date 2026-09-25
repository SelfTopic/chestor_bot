"""/clear_cooldown: снять кулдаун (конкретный или "all") у любого игрока — нужно для
эмпирической проверки случайных шансов, где ждать по 10 минут между попытками
нереально. Цель — ответ на сообщение или id/@username аргументом."""

from selfrot import BaseRouter, CommandArgs, MessageHandler
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from ...context import AppContext
from ...targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ...types import ReplyUserMessage, TextMessage


async def _perform_clear(
    ctx: AppContext[Message], telegram_id: int, type_name: str
) -> None:
    cooldown_service = ctx.cooldown_service

    if type_name.lower() == "all":
        count = await cooldown_service.clear_all_cooldowns(telegram_id)
        await ctx.message.answer(f"✅ Сброшено кулдаунов: {count}.")
        return

    cooldown_type = type_name.upper()
    known_types = await cooldown_service.list_cooldown_types()
    if cooldown_type not in known_types:
        await ctx.message.answer(
            f"❌ Неизвестный тип кулдауна. Доступны: {', '.join(known_types)}, all."
        )
        return

    cleared = await cooldown_service.clear_cooldown(telegram_id, cooldown_type)
    if not cleared:
        await ctx.message.answer(
            f"ℹ️ У пользователя не было активного кулдауна {cooldown_type}."
        )
        return

    await ctx.message.answer(f"✅ Кулдаун {cooldown_type} сброшен.")


class ClearCooldownRepliedArgs(CommandArgs):
    type_name: str


class ClearCooldownRepliedHandler(
    RepliedTargetHandler[ClearCooldownRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("clear_cooldown", ClearCooldownRepliedArgs)
    query = cmd & HasReplyUser()
    usage = "Использование (реплаем): /clear_cooldown <тип|all>"

    async def perform(self, telegram_id: int, args: ClearCooldownRepliedArgs) -> None:
        await _perform_clear(self.ctx, telegram_id, args.type_name)


class ClearCooldownArgs(TargetArgs):
    type_name: str


class ClearCooldownHandler(
    ExplicitTargetHandler[ClearCooldownArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("clear_cooldown", ClearCooldownArgs)
    query = cmd & ~HasReplyUser()
    usage = "Использование: /clear_cooldown <id или @username> <тип|all>"

    async def perform(self, telegram_id: int, args: ClearCooldownArgs) -> None:
        await _perform_clear(self.ctx, telegram_id, args.type_name)


class CooldownAdminRouter(BaseRouter[AppContext]):
    handlers = (ClearCooldownRepliedHandler, ClearCooldownHandler)
