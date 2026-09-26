from typing import Any, Generic, TypeVar

from selfrot import CommandArgs
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from ..context import AppContext
from ..services.lookup import find_user

TArgs = TypeVar("TArgs", bound=CommandArgs)


class _TargetErrors:
    usage: str = ""
    reply_errors: bool = False
    ctx: AppContext[Any]

    async def say(self, text: str) -> None:
        message = self.ctx.message
        await (message.reply(text) if self.reply_errors else message.answer(text))

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.say(self.usage)
            return

        raise exc


# Миксины не наследуют MessageHandler: selfrot проверяет заголовок только на прямых базах,
# поэтому хендлер сам пишет MessageHandler[...] вторым основанием.
class RepliedTargetHandler(_TargetErrors, Generic[TArgs]):
    cmd: Command[TArgs]

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        telegram_id: int = self.ctx.message.reply_to_message.user.id
        await self.perform(telegram_id, args)

    async def perform(self, telegram_id: int, args: TArgs) -> None:
        raise NotImplementedError


class TargetArgs(CommandArgs):
    target: str


TTargetArgs = TypeVar("TTargetArgs", bound=TargetArgs)


class ExplicitTargetHandler(_TargetErrors, Generic[TTargetArgs]):
    cmd: Command[TTargetArgs]
    not_found_text: str = "❌ Пользователь не найден: {target}"

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)

        user = await find_user(self.ctx.user_service, args.target)
        if user is None:
            await self.say(self.not_found_text.format(target=args.target))
            return

        await self.perform(user.telegram_id, args)

    async def perform(self, telegram_id: int, args: TTargetArgs) -> None:
        raise NotImplementedError
