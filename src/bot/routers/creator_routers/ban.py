import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.services.admin.ban import BanService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("ban_bot"))
@inject
async def ban_bot_user(
    message: Message, ban_service: BanService = Provide[Container.ban_service]
) -> None:
    if not message.text:
        raise ValueError("Сообщение не содержит текста")

    args = message.text.split(maxsplit=3)

    query = None
    reply = message.reply_to_message

    if reply and reply.from_user:
        query = str(reply.from_user.id)

    if len(args) < 2:
        await message.answer(
            "Использование: /ban <id или @username> [длительность] [причина]\n\n"
            "Длительность: 30m, 24h, 7d (без неё — перманентно)\n"
            "Примеры:\n"
            "/ban @username\n"
            "/ban 123456789 7d читерство\n"
            "/ban @username 24h флуд"
        )
        return

    query = query if query else args[1].strip()
    duration_str = (
        args[2].strip() if len(args) > 2 else args[1].strip() if len(args) > 1 else None
    )
    reason = (
        args[3].strip() if len(args) > 3 else args[2].strip() if len(args) > 2 else None
    )

    try:
        user = await ban_service._resolve_user(query)
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    if user.is_banned:
        await message.answer("⚠️ Пользователь уже забанен.")
        return

    result = await ban_service.ban(query, duration_str=duration_str, reason=reason)
    await message.answer(ban_service.format_ban_result(result), parse_mode="HTML")


@router.message(Command("unban"))
@inject
async def unban_user(
    message: Message, ban_service: BanService = Provide[Container.ban_service]
) -> None:
    if not message.text:
        raise ValueError("Сообщение не содержит текста")

    args = message.text.split(maxsplit=1)

    query = None
    reply = message.reply_to_message

    if reply and reply.from_user:
        args = [None, str(reply.from_user.id)]

    if len(args) < 2 and not (reply and reply.from_user):
        await message.answer("Использование: /unban <id или @username>")
        return

    query = query if query else args[1].strip()

    try:
        user = await ban_service._resolve_user(query)
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    if not user.is_banned:
        await message.answer("⚠️ Пользователь не забанен.")
        return

    unbanned = await ban_service.unban(query)
    await message.answer(
        f"✅ Пользователь <code>{unbanned.telegram_id}</code> ({unbanned.full_name}) разблокирован.",
        parse_mode="HTML",
    )
