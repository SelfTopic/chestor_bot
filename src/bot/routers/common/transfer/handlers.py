"""Начало перевода: команда с суммой в ответ на сообщение или с адресатом."""

from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import HasReplyUser, HasUser

from ....context import AppContext
from ...types import TextUserMessage, TextUserReplyMessage
from ...utils import full_name
from .commands import transfer_command
from .flow import ask_confirmation


class AmountArgs(CommandArgs):
    """/transfer 500 в ответ на сообщение получателя."""

    amount: int
    note: Rest = ""  # «перевести 500 за пиццу»: остаток игнорируется, как у прода


class TransferToRepliedHandler(MessageHandler[AppContext[TextUserReplyMessage]]):
    command = transfer_command(AmountArgs)
    query = command & HasUser() & HasReplyUser()
    usage = (
        "Укажи сумму перевода. Пример: /transfer 500 "
        "(или «перевести 500», «подать 500», «кинуть 500»)"
    )

    async def handle(self) -> None:
        args = self.command.parse(self.ctx)

        receiver = self.ctx.message.reply_to_message.user  # User: гарантия HasReplyUser

        await ask_confirmation(self.ctx, receiver.id, full_name(receiver), args.amount)

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.usage)
            return

        raise exc


class ReceiverArgs(CommandArgs):
    """/transfer @username 500 без ответа на сообщение."""

    receiver: str
    amount: int
    note: Rest = ""


class TransferToUserHandler(MessageHandler[AppContext[TextUserMessage]]):
    command = transfer_command(ReceiverArgs)
    query = command & HasUser() & ~HasReplyUser()
    usage = (
        "Использование:\n"
        "/transfer <сумма> — в ответ на сообщение получателя\n"
        "/transfer <id или @username> <сумма>\n\n"
        "Команду можно вызывать и так: перевести, подать, кинуть.\n"
        "Пример: /transfer @username 500 (или «кинуть @username 500»)"
    )

    async def handle(self) -> None:
        args = self.command.parse(self.ctx)

        query = args.receiver.strip()
        receiver = await self.ctx.transfer_service.resolve_user(query)
        if not receiver:
            await self.ctx.message.reply(f"❌ Пользователь не найден: {query}")
            return

        await ask_confirmation(
            self.ctx,
            receiver.telegram_id,
            receiver.username or receiver.first_name,
            args.amount,
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.usage)
            return

        raise exc
