"""Два шага подтверждения: нажатия кнопок под вопросом о переводе."""

import logging

from selfrot.filter import HasMessageCallbackQuery, InState
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import Message

from src.bot.exceptions import TransferError

from ....context import AppContext
from ...types import DataMessageCallbackQuery
from .flow import (
    CONFIRM_LABEL,
    TransferPress,
    TransferStates,
    build_confirmation_keyboard,
)

logger = logging.getLogger(__name__)


async def _cancel(ctx: AppContext[DataMessageCallbackQuery], message: Message) -> None:
    await ctx.fsm.clear()
    await message.edit_text("Перевод отменён.")
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
            f"Последнее подтверждение: перевести {data.amount} CheSton's? Это нельзя отменить.\n\n"
            f"Выбери именно кнопку «{CONFIRM_LABEL}» — остальные отменяют перевод.",
            reply_markup=build_confirmation_keyboard(step=2),
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
            await message.edit_text(f"❌ {e}")
            await callback.answer()
            return

        await message.edit_text(f"✅ Переведено {data.amount} CheSton's.")
        await callback.answer()
