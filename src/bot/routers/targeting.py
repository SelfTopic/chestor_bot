from typing import Any, Generic, TypeVar

from selfrot import CommandArgs, MessageHandler
from selfrot.exceptions import CommandArgsError
from selfrot.filter import AnyCommand, Command

from src.bot.dialogs import Dialogs, Line

from ..context import AppContext
from ..services.lookup import find_user

TArgs = TypeVar("TArgs", bound=CommandArgs)
TContext = TypeVar("TContext", bound=AppContext[Any])


# Ботов в users быть не должно, но на это не полагаемся: про реплай и кликабельное имя
# Telegram сам говорит is_bot, а свой id бот знает из токена.
def is_bot_target(ctx: AppContext[Any], telegram_id: int) -> bool:
    if telegram_id == ctx.bot.id:
        return True
    message = ctx.message
    replied = message.reply_to_message
    if replied is not None and replied.user is not None and replied.user.id == telegram_id:
        return replied.user.is_bot
    return any(user.id == telegram_id and user.is_bot for _, user in ctx.mentions())


class _TargetErrors:
    usage: Line | None = None
    reply_errors: bool = False
    ctx: AppContext[Any]

    async def say(self, line: Line) -> None:
        await self.ctx.say(line, reply=self.reply_errors)

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError) and self.usage is not None:
            await self.say(self.usage)
            return

        raise exc


class RepliedTargetHandler(_TargetErrors, MessageHandler[TContext], Generic[TArgs, TContext]):
    cmd: Command[TArgs] | AnyCommand[TArgs]

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        telegram_id: int = self.ctx.message.reply_to_message.user.id
        await self.perform(telegram_id, args)

    async def perform(self, telegram_id: int, args: TArgs) -> None:
        raise NotImplementedError


class TargetArgs(CommandArgs):
    target: str


TTargetArgs = TypeVar("TTargetArgs", bound=TargetArgs)


class ExplicitTargetHandler(
    _TargetErrors, MessageHandler[TContext], Generic[TTargetArgs, TContext]
):
    cmd: Command[TTargetArgs] | AnyCommand[TTargetArgs]

    def not_found(self, target: str) -> Line:
        return Dialogs.errors.user_not_found(query=target)

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        # Кликабельное имя человека без ника несёт его id: искать в базе не нужно.
        mentioned = self.ctx.mentions()
        if mentioned:
            await self.perform(mentioned[0][1].id, args)
            return

        user = await find_user(self.ctx.user_service, args.target)
        if user is None:
            await self.say(self.not_found(args.target))
            return

        await self.perform(user.telegram_id, args)

    async def perform(self, telegram_id: int, args: TTargetArgs) -> None:
        raise NotImplementedError
