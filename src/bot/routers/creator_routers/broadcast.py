import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.services.admin.broadcast import BroadcastService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("broadcast_private"))
@inject
async def broadcast_private(
    message: Message,
    broadcast_service: BroadcastService = Provide[Container.broadcast_service],
) -> None:
    args = message.text.split(maxsplit=1) if message.text else []
    if len(args) < 2:
        await message.answer("Использование: /broadcast_private <текст>")
        return

    await message.answer("📤 Рассылка запущена...")
    result = await broadcast_service.broadcast_to_private(args[1])
    await message.answer(
        f"✅ Рассылка завершена.\n"
        f"Всего: {result.total} | Успешно: {result.success} | Ошибок: {result.failed}"
    )


@router.message(Command("broadcast_chats"))
@inject
async def broadcast_chats(
    message: Message,
    broadcast_service: BroadcastService = Provide[Container.broadcast_service],
) -> None:
    args = message.text.split(maxsplit=1) if message.text else []
    if len(args) < 2:
        await message.answer("Использование: /broadcast_chats <текст>")
        return

    await message.answer("📤 Рассылка запущена...")
    result = await broadcast_service.broadcast_to_chats(args[1])
    await message.answer(
        f"✅ Рассылка завершена.\n"
        f"Всего: {result.total} | Успешно: {result.success} | Ошибок: {result.failed}"
    )


@router.message(Command("broadcast_all"))
@inject
async def broadcast_all(
    message: Message,
    broadcast_service: BroadcastService = Provide[Container.broadcast_service],
) -> None:
    args = message.text.split(maxsplit=1) if message.text else []
    if len(args) < 2:
        await message.answer("Использование: /broadcast_all <текст>")
        return

    await message.answer("📤 Рассылка запущена...")
    result = await broadcast_service.broadcast_to_all(args[1])
    await message.answer(
        f"✅ Рассылка завершена.\n"
        f"Всего: {result.total} | Успешно: {result.success} | Ошибок: {result.failed}"
    )


@router.message(Command("broadcast_user"))
@inject
async def broadcast_user(
    message: Message,
    broadcast_service: BroadcastService = Provide[Container.broadcast_service],
) -> None:
    # /broadcast_user <id или @username> <текст>
    args = message.text.split(maxsplit=2) if message.text else []
    if len(args) < 3:
        await message.answer(
            "Использование: /broadcast_user <id или @username> <текст>"
        )
        return

    try:
        ok = await broadcast_service.send_to_target(args[1], args[2])
        if ok:
            await message.answer("✅ Сообщение отправлено.")
        else:
            await message.answer(
                "❌ Не удалось отправить — пользователь заблокировал бота."
            )
    except ValueError as e:
        await message.answer(f"❌ {e}")
