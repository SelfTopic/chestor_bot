import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import LevelUpService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("force_levelup"))
@inject
async def force_levelup(
    message: Message,
    level_up_service: LevelUpService = Provide[Container.level_up_service],
) -> None:
    """Тестовая команда - вызывает LevelUpService.level_up() напрямую, без
    ожидания реального источника левел-апа (боя/поедания гулей), которого
    пока нет. См. BATTLE_DESIGN.md."""

    args = message.text.split(maxsplit=1) if message.text else []
    reply = message.reply_to_message

    if reply and reply.from_user:
        args = [None, str(reply.from_user.id)]

    if len(args) < 2:
        await message.answer("Использование: /force_levelup <id или @username>")
        return

    query = args[1].strip().lstrip("@")
    telegram_id = int(query) if query.isdigit() else None

    if telegram_id is None:
        await message.answer("❌ Укажи числовой telegram_id (по username пока нет резолва).")
        return

    try:
        result = await level_up_service.level_up(telegram_id)
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    await message.answer(
        f"✅ Уровень: {result.ghoul.level}. "
        f"CheSton: {result.cheston_reward}, RC: {result.rc_reward}. "
        f"ЛС доставлено: {'да' if result.notified else 'нет'}."
    )


__all__ = ["router"]
