"""Простые развлекательные команды для любых пользователей (не привязаны
к расе/гулю). Триггеры "бот"/"честор выбери/кто/случайный участник" -
явные, требуют обращения к боту по имени; калькулятор - единственное
исключение, слушает ЛЮБОЕ сообщение пассивно (см. `CalculatorFilter`,
паттерн - как у `RpCommandFilter`) и молчит, если выражение не разобралось
(никакого "❌ ошибка" в чат на случайный текст)."""

import logging
import random
import re
from typing import Any, Union

from aiogram import F, Router
from aiogram.filters import Filter
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import ChatService
from ...utils import CalculatorError, evaluate

router = Router(name=__name__)
logger = logging.getLogger(__name__)

_BOT_PREFIX = r"(?:бот|честор)"
_PICK_PATTERN = re.compile(rf"^{_BOT_PREFIX}\s+выбери\s+(.+)$", re.IGNORECASE | re.DOTALL)
_WHO_PATTERN = re.compile(rf"^{_BOT_PREFIX}\s+кто\s+(.+)$", re.IGNORECASE | re.DOTALL)
_RANDOM_PARTICIPANT_PATTERN = re.compile(
    rf"^{_BOT_PREFIX}\s+случайный\s+участник\s*$", re.IGNORECASE
)
_NUMBER_PATTERN = re.compile(
    rf"^{_BOT_PREFIX}\s+число\s+(-?\d+)\s+(-?\d+)\s*$", re.IGNORECASE
)
_ITEM_SEPARATOR = re.compile(r"\s*(?:,|\bили\b)\s*", re.IGNORECASE)

_MAX_PICK_ITEMS = 50
_MAX_ITEM_LENGTH = 200


async def _mention_random_participant(chat_service: ChatService, chat_id: int) -> str | None:
    """HTML-упоминание случайного участника чата, или None, если для
    чата ещё никого не записано (см. ChatParticipant)."""

    participant = await chat_service.get_random_participant(chat_id)
    if not participant:
        return None
    return f'<a href="tg://user?id={participant.telegram_id}">{participant.full_name}</a>'


@router.message(F.text.regexp(_PICK_PATTERN))
@inject
async def pick_handler(
    message: Message,
    chat_service: ChatService = Provide[Container.chat_service],
) -> None:
    if not message.text:
        return

    match = _PICK_PATTERN.match(message.text)
    if not match:
        return

    rest = match.group(1).strip()
    items = [item.strip() for item in _ITEM_SEPARATOR.split(rest) if item.strip()]

    if len(items) < 2:
        await message.reply(
            text='Нужно минимум 2 варианта: бот выбери пицца или суши или бургер'
        )
        return

    if len(items) > _MAX_PICK_ITEMS:
        await message.reply(text=f"Слишком много вариантов (максимум {_MAX_PICK_ITEMS}).")
        return

    if any(len(item) > _MAX_ITEM_LENGTH for item in items):
        await message.reply(text="Один из вариантов слишком длинный.")
        return

    await message.reply(text=f"🎲 Выбор пал на: {random.choice(items)}")


@router.message(F.text.regexp(_WHO_PATTERN))
@inject
async def who_handler(
    message: Message,
    chat_service: ChatService = Provide[Container.chat_service],
) -> None:
    if not message.text:
        return

    match = _WHO_PATTERN.match(message.text)
    if not match:
        return

    question = match.group(1).strip()

    mention = await _mention_random_participant(chat_service, message.chat.id)
    if not mention:
        await message.reply(
            text="Пока некого выбирать - в этом чате ещё никто не написал боту."
        )
        return

    await message.reply(
        text=f"По моим расчётам {question} {mention}",
        parse_mode="HTML",
    )


@router.message(F.text.regexp(_RANDOM_PARTICIPANT_PATTERN))
@inject
async def random_participant_handler(
    message: Message,
    chat_service: ChatService = Provide[Container.chat_service],
) -> None:
    mention = await _mention_random_participant(chat_service, message.chat.id)
    if not mention:
        await message.reply(
            text="Пока некого выбирать - в этом чате ещё никто не написал боту."
        )
        return

    await message.reply(text=f"🎲 Выбор пал на {mention}!", parse_mode="HTML")


@router.message(F.text.regexp(_NUMBER_PATTERN))
async def random_number_handler(message: Message) -> None:
    if not message.text:
        return

    match = _NUMBER_PATTERN.match(message.text)
    if not match:
        return

    low, high = int(match.group(1)), int(match.group(2))
    if low > high:
        low, high = high, low

    await message.reply(text=f"🎲 {random.randint(low, high)}")


class CalculatorFilter(Filter):
    """Пассивный триггер - пробует разобрать ЛЮБОЕ сообщение как
    арифметику (с хотя бы одним оператором, см. `evaluate(...,
    require_operator=True)`), молча пропускает (False), если не
    получилось - тот же паттерн, что уже используется `RpCommandFilter`."""

    async def __call__(self, message: Message) -> Union[bool, dict[str, Any]]:
        if not message.text:
            return False

        try:
            result = evaluate(message.text, require_operator=True)
        except CalculatorError:
            return False

        return {"calculator_result": result}


@router.message(CalculatorFilter())
async def calculator_handler(message: Message, calculator_result: Union[int, float]) -> None:
    result = calculator_result
    if isinstance(result, float) and result.is_integer():
        result = int(result)

    await message.reply(text=str(result))


__all__ = ["router", "CalculatorFilter"]
