import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import DialogService

logger = logging.getLogger(__name__)

router = Router(name=__name__)


@router.message(Command("help"))
@inject
async def help_handler(
    message: Message, dialog_service: DialogService = Provide[Container.dialog_service]
) -> Message:
    return await message.answer(
        text=dialog_service.text(
            key="help",
            commands_link="https://telegra.ph/CheStor-Chat-Bot-Commands-Ru-02-23",
            lore_link="Временно отсутствует",
        )
    )


__all__ = ["router"]
