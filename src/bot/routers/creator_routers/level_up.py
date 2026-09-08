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


@router.message(Command("add_progress"))
@inject
async def add_progress(
    message: Message,
    level_up_service: LevelUpService = Provide[Container.level_up_service],
) -> None:
    """Тестовая команда - начисляет level_progress напрямую (от -100 до 100),
    чтобы симулировать реальный источник левел-апа (бой/поедание гулей),
    которого пока нет, вместо прямого вызова /force_levelup. Пересечение
    100% триггерит level_up() как обычно - в т.ч. несколько раз подряд при
    большой дельте."""

    if not message.text:
        raise ValueError("Сообщение не содержит текста")

    reply = message.reply_to_message
    telegram_id = reply.from_user.id if reply and reply.from_user else None

    if telegram_id is not None:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "Использование (реплаем на сообщение цели): "
                "/add_progress <дельта от -100 до 100>"
            )
            return
        raw_delta = args[1].strip()
    else:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.answer(
                "Использование: /add_progress <id или @username> "
                "<дельта от -100 до 100>"
            )
            return
        query = args[1].strip().lstrip("@")
        if not query.isdigit():
            await message.answer(
                "❌ Укажи числовой telegram_id (по username пока нет резолва)."
            )
            return
        telegram_id = int(query)
        raw_delta = args[2].strip()

    try:
        delta = float(raw_delta)
    except ValueError:
        await message.answer("❌ Дельта должна быть числом.")
        return

    if not -100 <= delta <= 100:
        await message.answer("❌ Дельта должна быть в диапазоне от -100 до 100.")
        return

    try:
        result = await level_up_service.add_progress(telegram_id, delta)
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    lines = [
        f"✅ level_progress: {result.progress:.2f}%. "
        f"Уровней получено: {result.levels_gained}."
    ]
    for lvl_result in result.level_up_results:
        lines.append(
            f"  → уровень {lvl_result.ghoul.level}: "
            f"CheSton {lvl_result.cheston_reward}, RC {lvl_result.rc_reward}, "
            f"ЛС доставлено: {'да' if lvl_result.notified else 'нет'}"
        )

    await message.answer("\n".join(lines))


__all__ = ["router"]
