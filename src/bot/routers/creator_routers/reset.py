import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.services.admin.reset import ResetService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("reset_ghoul"))
@inject
async def reset_ghoul(
    message: Message,
    reset_service: ResetService = Provide[Container.reset_service],
) -> None:
    args = message.text.split(maxsplit=1) if message.text else []
    reply = message.reply_to_message

    if reply and reply.from_user:
        args = [None, str(reply.from_user.id)]

    if len(args) < 2:
        await message.answer("Использование: /reset_ghoul <id или @username>")
        return

    try:
        result = await reset_service.reset_ghoul(args[1].strip())
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    if not result.ghoul_deleted:
        await message.answer("⚠️ Профиль гуля не найден.")
        return

    await message.answer(
        f"✅ Профиль гуля пользователя <code>{result.telegram_id}</code> удалён.",
        parse_mode="HTML",
    )


@router.message(Command("reset_user"))
@inject
async def reset_user(
    message: Message,
    reset_service: ResetService = Provide[Container.reset_service],
) -> None:
    args = message.text.split(maxsplit=1) if message.text else []
    reply = message.reply_to_message

    if reply and reply.from_user:
        args = [None, str(reply.from_user.id)]

    if len(args) < 2:
        await message.answer("Использование: /reset_user <id или @username>")
        return

    try:
        result = await reset_service.reset_user(args[1].strip())
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    await message.answer(
        f"✅ Пользователь <code>{result.telegram_id}</code> полностью удалён.\n"
        f"Гуль удалён: {'да' if result.ghoul_deleted else 'не было'}",
        parse_mode="HTML",
    )
