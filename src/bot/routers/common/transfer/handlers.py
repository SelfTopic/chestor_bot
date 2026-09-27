from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import HasReplyUser, HasUser

from src.bot.dialogs import Dialogs

from ....context import AppContext
from ...types import TextUserMessage, TextUserReplyMessage
from ...utils import full_name
from .commands import transfer_command
from .flow import ask_confirmation


class AmountArgs(CommandArgs):
    amount: int
    note: Rest = ""


class TransferToRepliedHandler(MessageHandler[AppContext[TextUserReplyMessage]]):
    command = transfer_command(AmountArgs)
    query = command & HasUser() & HasReplyUser()
    usage = Dialogs.transfer.reply_usage()

    async def handle(self) -> None:
        args = self.command.parse(self.ctx)

        receiver = self.ctx.message.reply_to_message.user

        await ask_confirmation(self.ctx, receiver.id, full_name(receiver), args.amount)

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.ctx.text(self.usage))
            return

        raise exc


class ReceiverArgs(CommandArgs):
    receiver: str
    amount: int
    note: Rest = ""


class TransferToUserHandler(MessageHandler[AppContext[TextUserMessage]]):
    command = transfer_command(ReceiverArgs)
    query = command & HasUser() & ~HasReplyUser()
    usage = Dialogs.transfer.usage()

    async def handle(self) -> None:
        args = self.command.parse(self.ctx)

        query = args.receiver.strip()
        receiver = await self.ctx.transfer_service.resolve_user(query)
        if not receiver:
            await self.ctx.message.reply(
                self.ctx.text(Dialogs.errors.user_not_found(query=query))
            )
            return

        await ask_confirmation(
            self.ctx,
            receiver.telegram_id,
            receiver.username or receiver.first_name,
            args.amount,
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.ctx.text(self.usage))
            return

        raise exc
