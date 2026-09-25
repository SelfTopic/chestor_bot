"""
Каркас для команд «цель — ответ на сообщение или id/@username»: reply/explicit —
не текстовая условность, а два РАЗНЫХ класса хендлеров с разными гарантиями типов
(см. журнал порта: у прода общая функция с позиционными args по этой причине дважды
ловила баг со сдвигом индексов). Миксины здесь берут на себя только handle()/on_error(),
а конкретный MessageHandler[AppContext[X]] наследник указывает сам, вторым основанием:
библиотека находит заголовок по прямым generic-базам класса
(selfrot/handlers/base.py:_header_payload_type), а не по всей MRO, так что спрятать
его внутри миксина нельзя, не отключив проверку типа при импорте — здесь она,
как и everywhere в порте, остаётся явной.
"""

from typing import Any, Generic, TypeVar

from selfrot import CommandArgs
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from .context import AppContext
from .services.lookup import find_user

TArgs = TypeVar("TArgs", bound=CommandArgs)


class RepliedTargetHandler(Generic[TArgs]):
    """
    Цель — автор сообщения, на которое ответили. Наследник:
      - второе основание — MessageHandler[AppContext[X]], X включает ReplyUserMessage;
      - cmd: Command[TArgs], query = cmd & HasReplyUser();
      - usage (если у TArgs есть обязательные поля кроме цели — она и так из реплая),
      - perform(telegram_id, args).
    """

    cmd: Command[TArgs]
    usage: str = ""
    ctx: AppContext[Any]  # у наследника уже конкретный; здесь — общий для миксина

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        telegram_id: int = self.ctx.message.reply_to_message.user.id
        await self.perform(telegram_id, args)

    async def perform(self, telegram_id: int, args: TArgs) -> None:
        raise NotImplementedError

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.answer(self.usage)
            return

        raise exc


class TargetArgs(CommandArgs):
    """Форма аргументов explicit-варианта: первое слово — цель, остальное — своё."""

    target: str


TTargetArgs = TypeVar("TTargetArgs", bound=TargetArgs)


class ExplicitTargetHandler(Generic[TTargetArgs]):
    """
    Цель — id/@username аргументом. Наследник:
      - второе основание — MessageHandler[AppContext[X]] (обычно TextMessage);
      - cmd: Command[TTargetArgs] с моделью на основе TargetArgs, query = cmd & ~HasReplyUser();
      - usage, perform(telegram_id, args).
    """

    cmd: Command[TTargetArgs]
    usage: str = ""
    ctx: AppContext[Any]

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)

        user = await find_user(self.ctx.user_service, args.target)
        if user is None:
            await self.ctx.message.answer(f"❌ Пользователь не найден: {args.target}")
            return

        await self.perform(user.telegram_id, args)

    async def perform(self, telegram_id: int, args: TTargetArgs) -> None:
        raise NotImplementedError

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.answer(self.usage)
            return

        raise exc
