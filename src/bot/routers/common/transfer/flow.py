import random
from typing import Any, Literal

from pydantic import BaseModel
from selfrot import CallbackPayload, InlineKeyboard, State, States
from selfrot.types import InlineKeyboardMarkup

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import (
    InsufficientBalanceError,
    InvalidTransferAmountError,
    ReceiverLimitExceededError,
    ReceiverMissingError,
    ReceiverVanishedError,
    SelfTransferError,
    SenderMissingError,
    SenderTooNewError,
    TransferError,
)

from ....context import AppContext
from ...types import TextUserMessage

CONFIRM_BUTTON = Dialogs.transfer.buttons.confirm()
_CANCEL_BUTTONS = [
    Dialogs.transfer.buttons.decline(),
    Dialogs.transfer.buttons.surely_decline(),
    Dialogs.transfer.buttons.confirm_decline(),
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


def transfer_error_line(exc: TransferError) -> Line:
    errors = Dialogs.transfer.errors
    match exc:
        case InvalidTransferAmountError(min_amount=low, max_amount=high):
            return errors.amount_out_of_range(min_amount=low, max_amount=high)
        case SelfTransferError():
            return errors.self_transfer()
        case SenderMissingError():
            return errors.sender_missing()
        case SenderTooNewError(min_age_days=days):
            return errors.sender_too_new(days=days)
        case InsufficientBalanceError():
            return errors.insufficient_balance()
        case ReceiverMissingError():
            return errors.receiver_missing()
        case ReceiverVanishedError():
            return errors.receiver_vanished()
        case ReceiverLimitExceededError():
            return errors.receiver_limit()
        case _:
            return errors.failed()


def build_confirmation_keyboard(
    ctx: AppContext[Any], step: int
) -> InlineKeyboardMarkup:
    buttons = [
        (ctx.text(button), TransferPress(step=step, action="cancel"))
        for button in _CANCEL_BUTTONS
    ]
    buttons.append(
        (ctx.text(CONFIRM_BUTTON), TransferPress(step=step, action="confirm"))
    )
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
        await message.reply(ctx.text(transfer_error_line(e)))
        return

    await ctx.fsm.set(
        TransferStates.confirm_step_1,
        TransferData(receiver_id=receiver_id, amount=amount),
    )

    await message.reply(
        ctx.text(
            Dialogs.transfer.ask(
                amount=amount, receiver=receiver_name, confirm=ctx.text(CONFIRM_BUTTON)
            )
        ),
        reply_markup=build_confirmation_keyboard(ctx, step=1),
    )
