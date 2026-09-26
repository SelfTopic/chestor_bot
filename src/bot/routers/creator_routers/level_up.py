"""
/force_levelup и /add_progress: тестовые команды для боевой механики левелапа, см.
BATTLE_DESIGN.md. Цель — ответ на сообщение или id/@username аргументом, как у
остальных creator-команд.
"""

from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage

DELTA_RANGE_ERROR = "❌ Дельта должна быть в диапазоне от -100 до 100."


async def _perform_level_up(ctx: AppContext[Message], telegram_id: int) -> None:
    try:
        result = await ctx.level_up_service.level_up(telegram_id)
    except ValueError as e:
        await ctx.message.answer(f"❌ {e}")
        return

    await ctx.message.answer(
        f"✅ Уровень: {result.ghoul.level}. "
        f"CheSton: {result.cheston_reward}, RC: {result.rc_reward}. "
        f"ЛС доставлено: {'да' if result.notified else 'нет'}."
    )


class ForceLevelupRepliedArgs(CommandArgs):
    note: Rest = ""  # цель всё равно из реплая, что бы ни дописали после команды


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
    usage = "Использование: /force_levelup <id или @username>"

    async def perform(self, telegram_id: int, args: TargetArgs) -> None:
        await _perform_level_up(self.ctx, telegram_id)


async def _perform_add_progress(
    ctx: AppContext[Message], telegram_id: int, delta: float
) -> None:
    if not -100 <= delta <= 100:
        await ctx.message.answer(DELTA_RANGE_ERROR)
        return

    try:
        result = await ctx.level_up_service.add_progress(telegram_id, delta)
    except ValueError as e:
        await ctx.message.answer(f"❌ {e}")
        return

    lines = [
        f"✅ level_progress: {result.progress:.2f}%. "
        f"Уровней получено: {result.levels_gained}."
    ]
    for lvl_result in result.level_up_results:
        lines.append(
            f"  → уровень {lvl_result.ghoul.level}: "
            f"CheSton {lvl_result.cheston_reward}, RC {lvl_result.rc_reward}, "
            f"ЛС доставлено: {'да' if lvl_result.notified else 'нет'}"
        )

    await ctx.message.answer("\n".join(lines))


class AddProgressRepliedArgs(CommandArgs):
    delta: float


class AddProgressRepliedHandler(
    RepliedTargetHandler[AddProgressRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("add_progress", AddProgressRepliedArgs)
    query = cmd & HasReplyUser()
    usage = "Использование (реплаем на сообщение цели): /add_progress <дельта от -100 до 100>"

    async def perform(self, telegram_id: int, args: AddProgressRepliedArgs) -> None:
        await _perform_add_progress(self.ctx, telegram_id, args.delta)


class AddProgressArgs(TargetArgs):
    delta: float


class AddProgressHandler(
    ExplicitTargetHandler[AddProgressArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("add_progress", AddProgressArgs)
    query = cmd & ~HasReplyUser()
    usage = "Использование: /add_progress <id или @username> <дельта от -100 до 100>"

    async def perform(self, telegram_id: int, args: AddProgressArgs) -> None:
        await _perform_add_progress(self.ctx, telegram_id, args.delta)


class LevelUpRouter(BaseRouter[AppContext]):
    handlers = (
        ForceLevelupRepliedHandler,
        ForceLevelupHandler,
        AddProgressRepliedHandler,
        AddProgressHandler,
    )
