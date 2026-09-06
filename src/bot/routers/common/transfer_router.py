import logging
import random

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import TransferError
from ...services import TransferService

logger = logging.getLogger(__name__)
router = Router(name=__name__)


class TransferStates(StatesGroup):
    confirm_step_1 = State()
    confirm_step_2 = State()


_CANCEL_LABELS = [
    "не подтвердить",
    "точно не подтвердить",
    "подтвердить что не подтверждаю",
]
_CONFIRM_LABEL = "подтвердить"


def _build_confirmation_keyboard(step: int) -> InlineKeyboardMarkup:
    """Клавиатура-список из 4 кнопок, позиция настоящего "подтвердить" каждый
    раз перемешивается - нельзя механически тыкать в одно и то же место."""
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"transfer_cancel_{step}")
        for label in _CANCEL_LABELS
    ]
    buttons.append(
        InlineKeyboardButton(
            text=_CONFIRM_LABEL, callback_data=f"transfer_confirm_{step}"
        )
    )
    random.shuffle(buttons)

    return InlineKeyboardMarkup(inline_keyboard=[[button] for button in buttons])


@router.message(Command("transfer"))
@inject
async def transfer_handler(
    message: Message,
    state: FSMContext,
    transfer_service: TransferService = Provide[Container.transfer_service],
) -> None:
    if not message.from_user:
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply(
            "Ответь этой командой на сообщение того, кому хочешь перевести деньги.\n\n"
            "Пример: /transfer 500 (в ответ на сообщение получателя)"
        )
        return

    if not message.text:
        return

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("Укажи сумму перевода. Пример: /transfer 500")
        return

    amount = int(args[1])
    sender_id = message.from_user.id
    receiver_id = message.reply_to_message.from_user.id

    try:
        await transfer_service.validate(sender_id, receiver_id, amount)
    except TransferError as e:
        await message.reply(f"❌ {e}")
        return

    await state.update_data(receiver_id=receiver_id, amount=amount)
    await state.set_state(TransferStates.confirm_step_1)

    receiver_name = message.reply_to_message.from_user.full_name
    await message.reply(
        f"Перевести {amount} CheSton's пользователю {receiver_name}?\n\n"
        f"Выбери именно кнопку «{_CONFIRM_LABEL}» — остальные отменяют перевод.",
        reply_markup=_build_confirmation_keyboard(step=1),
    )


@router.callback_query(
    StateFilter(TransferStates.confirm_step_1),
    lambda c: c.data in ("transfer_confirm_1", "transfer_cancel_1"),
)
async def transfer_confirm_step_1(callback_query: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback_query.message, Message):
        return

    if callback_query.data == "transfer_cancel_1":
        await state.clear()
        await callback_query.message.edit_text("Перевод отменён.")
        await callback_query.answer()
        return

    data = await state.get_data()
    amount = data.get("amount")

    await state.set_state(TransferStates.confirm_step_2)
    await callback_query.message.edit_text(
        f"Последнее подтверждение: перевести {amount} CheSton's? Это нельзя отменить.\n\n"
        f"Выбери именно кнопку «{_CONFIRM_LABEL}» — остальные отменяют перевод.",
        reply_markup=_build_confirmation_keyboard(step=2),
    )
    await callback_query.answer()


@router.callback_query(
    StateFilter(TransferStates.confirm_step_2),
    lambda c: c.data in ("transfer_confirm_2", "transfer_cancel_2"),
)
@inject
async def transfer_confirm_step_2(
    callback_query: CallbackQuery,
    state: FSMContext,
    transfer_service: TransferService = Provide[Container.transfer_service],
) -> None:
    if not isinstance(callback_query.message, Message) or not callback_query.from_user:
        return

    if callback_query.data == "transfer_cancel_2":
        await state.clear()
        await callback_query.message.edit_text("Перевод отменён.")
        await callback_query.answer()
        return

    data = await state.get_data()
    receiver_id = data.get("receiver_id")
    amount = data.get("amount")
    sender_id = callback_query.from_user.id
    await state.clear()

    try:
        await transfer_service.validate(sender_id, receiver_id, amount)
        await transfer_service.transfer(sender_id, receiver_id, amount)
    except TransferError as e:
        logger.info(f"Transfer failed at final confirmation: {e}")
        await callback_query.message.edit_text(f"❌ {e}")
        await callback_query.answer()
        return

    await callback_query.message.edit_text(f"✅ Переведено {amount} CheSton's.")
    await callback_query.answer()


__all__ = ["router"]
