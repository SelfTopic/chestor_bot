import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.services.admin.stats_edit import StatsEditService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("set_stat"))
@inject
async def set_stat(
    message: Message,
    stats_service: StatsEditService = Provide[Container.stats_edit_service],
) -> None:
    if not message.text:
        raise ValueError("Сообщение не содержит текста")

    query = None
    reply = message.reply_to_message

    if reply and reply.from_user:
        query = str(reply.from_user.id)

    args = message.text.split(maxsplit=3)

    if len(args) < 4 and not query:
        await message.answer(
            f"Использование: /set_stat <id или @username> <поле> <значение>\n\n"
            f"{stats_service.format_fields_help()}"
        )
        return

    query, field, raw_value = args[1].strip(), args[2].strip(), args[3].strip()

    if not raw_value.lstrip("-").isdigit():
        await message.answer("❌ Значение должно быть целым числом.")
        return

    try:
        result = await stats_service.set_stat(query, field, int(raw_value))
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    target_label = "гуля" if result.is_ghoul_field else "пользователя"
    await message.answer(
        f"✅ Поле <code>{result.field}</code> {target_label} установлено в <code>{result.value}</code>.",
        parse_mode="HTML",
    )
