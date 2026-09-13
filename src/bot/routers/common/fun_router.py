"""Простые развлекательные команды для любых пользователей (не привязаны
к расе/гулю) - "выбери <список>" / "выбери участника" / "число <мин>
<макс>" / "посчитай <выражение>". Никакого игрового состояния не меняют,
кроме "выбери участника" (читает ChatParticipant, см. SyncEntitiesService)."""

import logging
import random
import re

from aiogram import Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...filters import Text
from ...services import ChatService
from ...utils import CalculatorError, evaluate

router = Router(name=__name__)
logger = logging.getLogger(__name__)

_PICK_PATTERN = re.compile(r"^выбери\s+(.+)$", re.IGNORECASE | re.DOTALL)
_NUMBER_PATTERN = re.compile(r"^число\s+(-?\d+)\s+(-?\d+)\s*$", re.IGNORECASE)
_CALC_PATTERN = re.compile(r"^посчитай\s+(.+)$", re.IGNORECASE | re.DOTALL)

_MAX_PICK_ITEMS = 50
_MAX_ITEM_LENGTH = 200


@router.message(Text(command="выбери", startswith=True))
@inject
async def pick_handler(
    message: Message,
    chat_service: ChatService = Provide[Container.chat_service],
) -> None:
    if not message.text:
        return

    match = _PICK_PATTERN.match(message.text)
    if not match:
        await message.reply(
            text='Использование: выбери <вариант1>, <вариант2>, ... или "выбери участника"'
        )
        return

    rest = match.group(1).strip()

    if rest.lower() == "участника":
        participant = await chat_service.get_random_participant(message.chat.id)
        if not participant:
            await message.reply(
                text="Пока некого выбирать - в этом чате ещё никто не написал боту."
            )
            return

        await message.reply(
            text=(
                f'🎲 Выбор пал на <a href="tg://user?id={participant.telegram_id}">'
                f"{participant.full_name}</a>!"
            ),
            parse_mode="HTML",
        )
        return

    items = [item.strip() for item in rest.split(",") if item.strip()]

    if len(items) < 2:
        await message.reply(
            text="Нужно минимум 2 варианта через запятую: выбери пицца, суши, бургер"
        )
        return

    if len(items) > _MAX_PICK_ITEMS:
        await message.reply(text=f"Слишком много вариантов (максимум {_MAX_PICK_ITEMS}).")
        return

    if any(len(item) > _MAX_ITEM_LENGTH for item in items):
        await message.reply(text="Один из вариантов слишком длинный.")
        return

    await message.reply(text=f"🎲 Выбор пал на: {random.choice(items)}")


@router.message(Text(command="число", startswith=True))
async def random_number_handler(message: Message) -> None:
    if not message.text:
        return

    match = _NUMBER_PATTERN.match(message.text)
    if not match:
        await message.reply(
            text="Использование: число <мин> <макс>, например: число 1 100"
        )
        return

    low, high = int(match.group(1)), int(match.group(2))
    if low > high:
        low, high = high, low

    await message.reply(text=f"🎲 {random.randint(low, high)}")


@router.message(Text(command="посчитай", startswith=True))
async def calculator_handler(message: Message) -> None:
    if not message.text:
        return

    match = _CALC_PATTERN.match(message.text)
    if not match:
        await message.reply(
            text="Использование: посчитай <выражение>, например: посчитай (2+2)*10"
        )
        return

    expression = match.group(1).strip()

    try:
        result = evaluate(expression)
    except CalculatorError as e:
        await message.reply(text=f"❌ {e}")
        return

    if isinstance(result, float) and result.is_integer():
        result = int(result)

    await message.reply(text=f"🧮 {result}")


__all__ = ["router"]
