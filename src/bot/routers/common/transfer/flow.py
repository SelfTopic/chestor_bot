import random
from typing import Literal

from pydantic import BaseModel
from selfrot import CallbackPayload, InlineKeyboard, State, States
from selfrot.types import InlineKeyboardMarkup

from src.bot.exceptions import TransferError

from ....context import AppContext
from ...types import TextUserMessage

CONFIRM_LABEL = "подтвердить"
_CANCEL_LABELS = [
    "не подтвердить",
    "точно не подтвердить",
    "подтвердить что не подтверждаю",
]


class TransferData(BaseModel):
    receiver_id: int
    amount: int


class TransferStates(States):
    confirm_step_1 = State(TransferData)
    confirm_step_2 = State(TransferData)


class TransferPress(CallbackPayload, prefix="transfer"):
    step: int
    action: Literal["confirm", "cancel"]


def build_confirmation_keyboard(step: int) -> InlineKeyboardMarkup:
    buttons = [
        (label, TransferPress(step=step, action="cancel")) for label in _CANCEL_LABELS
    ]
    buttons.append((CONFIRM_LABEL, TransferPress(step=step, action="confirm")))
    random.shuffle(buttons)

    keyboard = InlineKeyboard()
    for label, payload in buttons:
        keyboard.button(label, payload)

    return keyboard.markup()


async def ask_confirmation(
    ctx: AppContext[TextUserMessage],
    receiver_id: int,
    receiver_name: str,
    amount: int,
) -> None:
    message = ctx.message

    try:
        await ctx.transfer_service.validate(message.user.id, receiver_id, amount)
    except TransferError as e:
        await message.reply(f"❌ {e}")
        return

    await ctx.fsm.set(
        TransferStates.confirm_step_1,
        TransferData(receiver_id=receiver_id, amount=amount),
    )

    await message.reply(
        f"Перевести {amount} CheSton's пользователю {receiver_name}?\n\n"
        f"Выбери именно кнопку «{CONFIRM_LABEL}» — остальные отменяют перевод.",
        reply_markup=build_confirmation_keyboard(step=1),
    )
