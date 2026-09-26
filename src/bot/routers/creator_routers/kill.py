"""/kill_ghoul: тестовая команда, мгновенно убивает гуля (apply_death) тем же путём,
что настоящая смерть — is_dead, запись в death_log, некролог через NotificationTicker.
Цель — ответ на сообщение или id/@username аргументом."""

from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import Command, HasReplyUser
from selfrot.types import Message

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import ReplyUserMessage, TextMessage


class KillGhoulRepliedArgs(CommandArgs):
    cause: Rest = ""


async def _perform_kill(ctx: AppContext[Message], telegram_id: int, cause: str) -> None:
    try:
        updated = await ctx.ghoul_service.apply_death(
            telegram_id, cause=cause or "admin"
        )
    except ValueError as e:
        await ctx.message.answer(f"❌ {e}")
        return

    await ctx.message.answer(
        f"💀 Гуль <code>{telegram_id}</code> убит (причина: {cause or 'admin'}). "
        f"Смертей: {updated.deaths}. Некролог придёт с ближайшим тиком (≤30с).",
        parse_mode="HTML",
    )


class KillGhoulRepliedHandler(
    RepliedTargetHandler[KillGhoulRepliedArgs],
    MessageHandler[AppContext[ReplyUserMessage]],
):
    cmd = Command("kill_ghoul", KillGhoulRepliedArgs)
    query = cmd & HasReplyUser()

    async def perform(self, telegram_id: int, args: KillGhoulRepliedArgs) -> None:
        await _perform_kill(self.ctx, telegram_id, args.cause)


class KillGhoulArgs(TargetArgs):
    cause: Rest = ""


class KillGhoulHandler(
    ExplicitTargetHandler[KillGhoulArgs],
    MessageHandler[AppContext[TextMessage]],
):
    cmd = Command("kill_ghoul", KillGhoulArgs)
    query = cmd & ~HasReplyUser()
    usage = "Использование: /kill_ghoul <id или @username> [причина]"

    async def perform(self, telegram_id: int, args: KillGhoulArgs) -> None:
        await _perform_kill(self.ctx, telegram_id, args.cause)


class KillRouter(BaseRouter[AppContext]):
    handlers = (KillGhoulRepliedHandler, KillGhoulHandler)
