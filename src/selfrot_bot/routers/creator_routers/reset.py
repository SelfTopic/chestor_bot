"""/reset_ghoul и /reset_user: цель — ответ на сообщение или id/@username аргументом."""

from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage


class ResetRepliedArgs(CommandArgs):
    note: Rest = ""  # цель всё равно из реплая, что бы ни дописали после команды


async def _perform_reset_ghoul(ctx: AppContext[Message], target: str) -> None:
    try:
        result = await ctx.reset_service.reset_ghoul(target)
    except ValueError as e:
        await ctx.message.answer(f"❌ {e}")
        return

    if not result.ghoul_deleted:
        await ctx.message.answer("⚠️ Профиль гуля не найден.")
        return

    await ctx.message.answer(
        f"✅ Профиль гуля пользователя <code>{result.telegram_id}</code> удалён.",
        parse_mode="HTML",
    )


class ResetGhoulRepliedHandler(
    RepliedTargetHandler[ResetRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("reset_ghoul", ResetRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: ResetRepliedArgs) -> None:
        await _perform_reset_ghoul(self.ctx, str(telegram_id))


class ResetGhoulHandler(
    ExplicitTargetHandler[TargetArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("reset_ghoul", TargetArgs)
    query = cmd & ~HasReplyUser()
    usage = "Использование: /reset_ghoul <id или @username>"

    async def perform(self, telegram_id: int, args: TargetArgs) -> None:
        await _perform_reset_ghoul(self.ctx, str(telegram_id))


async def _perform_reset_user(ctx: AppContext[Message], target: str) -> None:
    try:
        result = await ctx.reset_service.reset_user(target)
    except ValueError as e:
        await ctx.message.answer(f"❌ {e}")
        return

    await ctx.message.answer(
        f"✅ Пользователь <code>{result.telegram_id}</code> полностью удалён.\n"
        f"Гуль удалён: {'да' if result.ghoul_deleted else 'не было'}",
        parse_mode="HTML",
    )


class ResetUserRepliedHandler(
    RepliedTargetHandler[ResetRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("reset_user", ResetRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: ResetRepliedArgs) -> None:
        await _perform_reset_user(self.ctx, str(telegram_id))


class ResetUserHandler(
    ExplicitTargetHandler[TargetArgs], MessageHandler[AppContext[TextMessage]]
):
    cmd = Command("reset_user", TargetArgs)
    query = cmd & ~HasReplyUser()
    usage = "Использование: /reset_user <id или @username>"

    async def perform(self, telegram_id: int, args: TargetArgs) -> None:
        await _perform_reset_user(self.ctx, str(telegram_id))


class ResetRouter(BaseRouter[AppContext]):
    handlers = (
        ResetGhoulRepliedHandler,
        ResetGhoulHandler,
        ResetUserRepliedHandler,
        ResetUserHandler,
    )
