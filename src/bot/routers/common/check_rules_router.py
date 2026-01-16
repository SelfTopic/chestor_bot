from aiogram import Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import ChatNotFoundInDatabase
from ...filters import Text
from ...services import ChatService

router = Router(name=__name__)


@router.message(Text("правила"))
@inject
async def check_chat_rules_handler(
    message: Message, chat_service: ChatService = Provide[Container.chat_service]
) -> None:
    chat = await chat_service.get_by_telegram_id(telegram_id=message.chat.id)

    if not chat:
        raise ChatNotFoundInDatabase()

    if not chat.rules:
        await message.answer(
            "В этом чате правила отсутствуют. Чтобы указать новые правила используйте команду 'новые правила'"
        )
        return

    await message.answer(chat.rules)
