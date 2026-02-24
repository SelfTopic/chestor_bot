import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.services.admin.player_lookup import PlayerLookupService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("admin_profile"))
@inject
async def admin_profile(
    message: Message,
    player_lookup_service: PlayerLookupService = Provide[
        Container.player_lookup_service
    ],
) -> None:
    if not message.text:
        raise ValueError("Сообщение не содержит текста")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: /admin_profile <telegram_id или @username>"
        )
        return

    profile = await player_lookup_service.get_profile(args[1].strip())
    if not profile:
        await message.answer("❌ Пользователь не найден.")
        return

    await message.answer(
        player_lookup_service.format_profile(profile), parse_mode="HTML"
    )
