from selfrot import BaseRouter, CommandArgs, MessageHandler
from selfrot.filter import Command, HasReplyUser, HasUser
from selfrot.types import Message

from src.bot.services.admin.stats_edit import (
    ALLOWED_GHOUL_FIELDS,
    ALLOWED_GHOUL_TIME_FIELDS,
    ALLOWED_USER_FIELDS,
)

from ...context import AppContext
from ..targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ..types import TextUserMessage, TextUserReplyMessage

# Подсказка — константа модуля: в on_error сессия уже закрыта, сервисы из контекста
# недоступны.
USAGE = (
    "Использование: /set_stat <id или @username> <поле> <значение>\n\n"
    f"Поля пользователя: {', '.join(sorted(ALLOWED_USER_FIELDS))}\n"
    f"Поля гуля: {', '.join(sorted(ALLOWED_GHOUL_FIELDS))}\n"
    f"Служебные поля гуля (сдвиг снапшота назад на N часов, для теста "
    f"голода/регена): {', '.join(sorted(ALLOWED_GHOUL_TIME_FIELDS))}"
)


async def _perform_set_stat(
    ctx: AppContext[Message], target: str, field: str, value: int, admin_id: int
) -> None:
    try:
        result = await ctx.stats_edit_service.set_stat(
            target, field, value, admin_id=admin_id
        )
    except ValueError as e:
        await ctx.message.answer(f"❌ {e}")
        return

    target_label = "гуля" if result.is_ghoul_field else "пользователя"
    await ctx.message.answer(
        f"✅ Поле <code>{result.field}</code> {target_label} установлено в "
        f"<code>{result.value}</code>.",
        parse_mode="HTML",
    )


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
