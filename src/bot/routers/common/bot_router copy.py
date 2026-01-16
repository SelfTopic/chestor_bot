import logging

from aiogram import F, Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import DialogService

logger = logging.getLogger(__name__)

router = Router(name=__name__)


@router.message(F.text.lower() == "бот")
@inject
async def bot_handler(
    message: Message, dialog_service: DialogService = Provide[Container.dialog_service]
) -> Message:
    return await message.answer(
        text=dialog_service.random(
            key="bot",
        )
    )


__all__ = ["router"]
