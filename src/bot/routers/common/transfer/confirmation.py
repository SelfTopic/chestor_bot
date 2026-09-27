import logging

from selfrot.filter import HasMessageCallbackQuery, InState
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.exceptions import TransferError

from ....context import AppContext
from ...types import DataMessageCallbackQuery
from .flow import (
    CONFIRM_BUTTON,
    TransferPress,
    TransferStates,
    build_confirmation_keyboard,
    transfer_error_line,
)

logger = logging.getLogger(__name__)


async def _cancel(ctx: AppContext[DataMessageCallbackQuery], message: Message) -> None:
    await ctx.fsm.clear()
    await message.edit_text(ctx.text(Dialogs.transfer.cancelled()))
    await ctx.callback_query.answer()


class TransferStep1Handler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = TransferPress.filter(step=1)
    query = InState(TransferStates.confirm_step_1) & press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        callback = self.ctx.callback_query
        message = callback.message

        if not isinstance(message, Message):
            return

        if self.press.parse(self.ctx).action == "cancel":
            await _cancel(self.ctx, message)
            return

        data = await self.ctx.fsm.get(TransferStates.confirm_step_1)

        await self.ctx.fsm.set(TransferStates.confirm_step_2, data)
        await message.edit_text(
            self.ctx.text(
                Dialogs.transfer.ask_again(
                    amount=data.amount, confirm=self.ctx.text(CONFIRM_BUTTON)
                )
            ),
            reply_markup=build_confirmation_keyboard(self.ctx, step=2),
        )
        await callback.answer()


class TransferStep2Handler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = TransferPress.filter(step=2)
    query = InState(TransferStates.confirm_step_2) & press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        callback = self.ctx.callback_query
        message = callback.message

        if not isinstance(message, Message):
            return

        if self.press.parse(self.ctx).action == "cancel":
            await _cancel(self.ctx, message)
            return

        data = await self.ctx.fsm.get(TransferStates.confirm_step_2)
        await self.ctx.fsm.clear()

        transfer_service = self.ctx.transfer_service
        sender_id = callback.user.id

        try:
            await transfer_service.validate(sender_id, data.receiver_id, data.amount)
            await transfer_service.transfer(sender_id, data.receiver_id, data.amount)
        except TransferError as e:
            logger.info(f"Transfer failed at final confirmation: {e}")
            await message.edit_text(self.ctx.text(transfer_error_line(e)))
            await callback.answer()
            return

        await message.edit_text(
            self.ctx.text(Dialogs.transfer.done(amount=data.amount))
        )
        await callback.answer()
