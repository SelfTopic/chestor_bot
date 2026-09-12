import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import CooldownService

logger = logging.getLogger(__name__)
router = Router()


def _resolve_target(message: Message) -> tuple[list[str], int | None]:
    """Тот же паттерн, что в kagune_admin.py - id/@username аргументом или
    реплай на сообщение цели (дублируется намеренно, отдельной shared-
    утилиты под это в проекте нет ни разу)."""

    reply = message.reply_to_message
    if reply and reply.from_user:
        args = message.text.split(maxsplit=1) if message.text else []
        return args, reply.from_user.id

    args = message.text.split(maxsplit=2) if message.text else []
    return args, None


@router.message(Command("clear_cooldown"))
@inject
async def clear_cooldown(
    message: Message,
    cooldown_service: CooldownService = Provide[Container.cooldown_service],
) -> None:
    """Снять конкретный (или все разом - "all") кулдаун у ЛЮБОГО игрока -
    нужно для эмпирической проверки случайных шансов (например будущей
    засады моба во время поедания человека), где ждать по 10 минут между
    попытками нереально."""

    args, telegram_id = _resolve_target(message)

    if telegram_id is not None:
        if len(args) < 2:
            await message.answer(
                "Использование (реплаем): /clear_cooldown <тип|all>"
            )
            return
        type_name = args[1].strip()
    else:
        if len(args) < 3:
            await message.answer(
                "Использование: /clear_cooldown <id или @username> <тип|all>"
            )
            return
        query = args[1].strip().lstrip("@")
        if not query.isdigit():
            await message.answer(
                "❌ Укажи числовой telegram_id (по username пока нет резолва)."
            )
            return
        telegram_id = int(query)
        type_name = args[2].strip()

    if type_name.lower() == "all":
        count = await cooldown_service.clear_all_cooldowns(telegram_id)
        await message.answer(f"✅ Сброшено кулдаунов: {count}.")
        return

    cooldown_type = type_name.upper()
    known_types = await cooldown_service.list_cooldown_types()
    if cooldown_type not in known_types:
        await message.answer(
            f"❌ Неизвестный тип кулдауна. Доступны: {', '.join(known_types)}, all."
        )
        return

    cleared = await cooldown_service.clear_cooldown(telegram_id, cooldown_type)
    if not cleared:
        await message.answer(f"ℹ️ У пользователя не было активного кулдауна {cooldown_type}.")
        return

    await message.answer(f"✅ Кулдаун {cooldown_type} сброшен.")


__all__ = ["router"]
