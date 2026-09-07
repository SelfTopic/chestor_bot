import logging
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import CooldownService, DialogService, GhoulService, MediaService
from ...utils import parse_seconds

router = Router(name=__name__)

logger = logging.getLogger(__name__)

COOLDOWN_NAME = "EAT_HUMAN"


@router.message(F.text.lower() == "сожрать человека")
@inject
async def eat_human_handler(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    cooldown_service: CooldownService = Provide[Container.cooldown_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
    media_service: MediaService = Provide[Container.media_service],
) -> None:
    if not message.from_user:
        logger.warning("User not found")
        return None

    user_cooldown = await cooldown_service.get_active_cooldown(
        telegram_id=message.from_user.id, cooldown_name=COOLDOWN_NAME
    )

    if user_cooldown:
        cooldown_remaining = parse_seconds(
            total_seconds=int(user_cooldown.end_at - time.time())
        )
        await message.reply(
            text=dialog_service.text(
                key="eat_human_cooldown_error",
                hours=cooldown_remaining.total_hours,
                minutes=cooldown_remaining.minutes_remaining,
                seconds=cooldown_remaining.seconds_remaining,
            )
        )
        return None

    ghoul, restored = await ghoul_service.eat_human(telegram_id=message.from_user.id)

    await cooldown_service.set_cooldown(
        telegram_id=message.from_user.id, cooldown_type=COOLDOWN_NAME
    )

    caption = dialog_service.text(
        key="eat_human_accept",
        restored=restored,
        hunger=ghoul.hunger,
        count=ghoul.eat_humans,
    )

    media = await media_service.get_random_gif(
        "eat human", user_id=message.from_user.id
    )

    if not media:
        await message.reply(text=caption)
        return None

    logger.debug(f"Media path: {media.path}, media file_id: {media.telegram_file_id}")

    try:
        await message.reply_animation(
            animation=media.telegram_file_id or FSInputFile(media.path),
            caption=caption,
        )

    except TelegramBadRequest:
        my_message = await message.reply_animation(
            animation=FSInputFile(media.path), caption=caption
        )

        if not my_message.animation:
            raise
        await media_service.update_telegram_file_id(
            path=media.path, new_file_id=my_message.animation.file_id
        )

    return None


__all__ = ["router"]
