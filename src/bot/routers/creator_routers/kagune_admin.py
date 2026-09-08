import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import GhoulService
from ...types import KaguneType

logger = logging.getLogger(__name__)
router = Router()

_TYPE_BY_NAME = {kt.value["name_english"]: kt for kt in KaguneType}
_TYPE_NAMES = ", ".join(sorted(_TYPE_BY_NAME))


def _resolve_target(message: Message) -> tuple[list[str], int | None]:
    """Общий для всех creator-команд паттерн: id/@username явным аргументом
    или реплай на сообщение цели."""
    reply = message.reply_to_message
    if reply and reply.from_user:
        args = message.text.split(maxsplit=1) if message.text else []
        return args, reply.from_user.id

    args = message.text.split(maxsplit=2) if message.text else []
    return args, None


@router.message(Command("give_kagune"))
@inject
async def give_kagune(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
) -> None:
    args, telegram_id = _resolve_target(message)

    if telegram_id is not None:
        if len(args) < 2:
            await message.answer(
                f"Использование (реплаем): /give_kagune <{_TYPE_NAMES}|all>"
            )
            return
        type_name = args[1].strip().lower()
    else:
        if len(args) < 3:
            await message.answer(
                f"Использование: /give_kagune <id или @username> <{_TYPE_NAMES}|all>"
            )
            return
        query = args[1].strip().lstrip("@")
        if not query.isdigit():
            await message.answer(
                "❌ Укажи числовой telegram_id (по username пока нет резолва)."
            )
            return
        telegram_id = int(query)
        type_name = args[2].strip().lower()

    try:
        if type_name == "all":
            ghoul = await ghoul_service.grant_all_kagune_types(telegram_id)
            await message.answer(
                f"✅ Выданы все типы кагуне. Открыто: "
                f"{', '.join(kt.value['name'] for kt in ghoul_service.owned_kagune_types(ghoul))}."
            )
            return

        kagune_type = _TYPE_BY_NAME.get(type_name)
        if kagune_type is None:
            await message.answer(f"❌ Неизвестный тип. Доступны: {_TYPE_NAMES}, all.")
            return

        ghoul = await ghoul_service.grant_kagune_type(telegram_id, kagune_type)
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        await message.answer(
            f"✅ Выдан тип {kagune_type.value['name']} (сила {strength})."
        )
    except ValueError as e:
        await message.answer(f"❌ {e}")


@router.message(Command("remove_kagune"))
@inject
async def remove_kagune(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
) -> None:
    args, telegram_id = _resolve_target(message)

    if telegram_id is not None:
        if len(args) < 2:
            await message.answer(f"Использование (реплаем): /remove_kagune <{_TYPE_NAMES}>")
            return
        type_name = args[1].strip().lower()
    else:
        if len(args) < 3:
            await message.answer(
                f"Использование: /remove_kagune <id или @username> <{_TYPE_NAMES}>"
            )
            return
        query = args[1].strip().lstrip("@")
        if not query.isdigit():
            await message.answer(
                "❌ Укажи числовой telegram_id (по username пока нет резолва)."
            )
            return
        telegram_id = int(query)
        type_name = args[2].strip().lower()

    kagune_type = _TYPE_BY_NAME.get(type_name)
    if kagune_type is None:
        await message.answer(f"❌ Неизвестный тип. Доступны: {_TYPE_NAMES}.")
        return

    try:
        await ghoul_service.revoke_kagune_type(telegram_id, kagune_type)
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    await message.answer(f"✅ Тип {kagune_type.value['name']} убран.")


__all__ = ["router"]
