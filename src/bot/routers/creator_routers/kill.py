import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import GhoulService, UserService

logger = logging.getLogger(__name__)
router = Router()


async def _resolve_telegram_id(query: str, user_service: UserService) -> int | None:
    """id или @username в telegram_id - тот же приём, что уже используют
    BanService._resolve_user/ResetService/PlayerLookupService/BroadcastService."""

    search = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
    user = await user_service.get(search)
    return user.telegram_id if user else None


@router.message(Command("kill_ghoul"))
@inject
async def kill_ghoul(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    user_service: UserService = Provide[Container.user_service],
) -> None:
    """Тестовая команда - мгновенно убивает гуля (apply_death) напрямую, не
    дожидаясь реального триггера (голод в минус / поедание после боя). Тот
    же путь, что и настоящая смерть - is_dead, запись в death_log, некролог
    через тикер. См. BATTLE_DESIGN.md ("Смерть и сброс")."""

    if not message.text:
        raise ValueError("Сообщение не содержит текста")

    reply = message.reply_to_message
    telegram_id = reply.from_user.id if reply and reply.from_user else None

    if telegram_id is not None:
        args = message.text.split(maxsplit=1)
        cause = args[1].strip() if len(args) >= 2 else "admin"
    else:
        args = message.text.split(maxsplit=2)
        if len(args) < 2:
            await message.answer(
                "Использование: /kill_ghoul <id или @username> [причина]"
            )
            return

        query = args[1].strip()
        telegram_id = await _resolve_telegram_id(query, user_service)
        if telegram_id is None:
            await message.answer(f"❌ Пользователь не найден: {query}")
            return

        cause = args[2].strip() if len(args) >= 3 else "admin"

    try:
        updated = await ghoul_service.apply_death(telegram_id, cause=cause)
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    await message.answer(
        f"💀 Гуль <code>{telegram_id}</code> убит (причина: {cause}). "
        f"Смертей: {updated.deaths}. Некролог придёт с ближайшим тиком (≤30с).",
        parse_mode="HTML",
    )


__all__ = ["router"]
