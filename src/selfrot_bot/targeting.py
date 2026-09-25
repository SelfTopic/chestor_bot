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


class _TargetErrors:
    """Ответы на ошибки аргументов, общие для обоих миксинов."""

    usage: str = ""
    # True — ошибкой отвечать реплаем на команду (как прод-«дуэль»), а не отдельным сообщением.
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


class RepliedTargetHandler(_TargetErrors, Generic[TArgs]):
    """
    Цель — автор сообщения, на которое ответили. Наследник:
      - второе основание — MessageHandler[AppContext[X]], X включает ReplyUserMessage;
      - cmd: Command[TArgs], query = cmd & HasReplyUser();
      - usage (если у TArgs есть обязательные поля кроме цели — она и так из реплая),
      - perform(telegram_id, args).
    """

    cmd: Command[TArgs]

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        telegram_id: int = self.ctx.message.reply_to_message.user.id
        await self.perform(telegram_id, args)

    async def perform(self, telegram_id: int, args: TArgs) -> None:
        raise NotImplementedError


class TargetArgs(CommandArgs):
    """Форма аргументов explicit-варианта: первое слово — цель, остальное — своё."""

    target: str


TTargetArgs = TypeVar("TTargetArgs", bound=TargetArgs)


class ExplicitTargetHandler(_TargetErrors, Generic[TTargetArgs]):
    """
    Цель — id/@username аргументом. Наследник:
      - второе основание — MessageHandler[AppContext[X]] (обычно TextMessage);
      - cmd: Command[TTargetArgs] с моделью на основе TargetArgs, query = cmd & ~HasReplyUser();
      - usage, perform(telegram_id, args).
    """

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
