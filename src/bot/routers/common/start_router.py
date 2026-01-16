import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import DialogService, UserService

logger = logging.getLogger(__name__)

router = Router(name=__name__)


@router.message(CommandStart(deep_link=False))
@inject
async def start_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
) -> Message:
    if not message.from_user:
        logger.error("User not found")
        raise ValueError("User not found")

    user = await user_service.get(message.from_user.id)

    if not user:
        logger.error("User not found in database")
        raise ValueError("User not found in database")

    logger.debug(f"User equal {user}")

    return await message.answer(
        text=dialog_service.text(
            key="start",
            name=user.first_name or "User",
        )
    )


__all__ = ["router"]
