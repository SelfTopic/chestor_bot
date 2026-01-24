import logging
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.game_configs import SNAP_CONFIG
from src.bot.services import (
    CooldownService,
    DialogService,
    GhoulService,
    MediaService,
    UserService,
)
from src.bot.utils import parse_seconds

router = Router(name=__name__)

logger = logging.getLogger(__name__)


@router.message(F.text.lower() == "щелк")
@inject
async def snap_handler(
    message: Message,
    dialog_service: DialogService = Provide[Container.dialog_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    cooldown_service: CooldownService = Provide[Container.cooldown_service],
    user_service: UserService = Provide[Container.user_service],
    media_service: MediaService = Provide[Container.media_service],
) -> None:
    if not message.from_user:
        logger.warning("User not found")
        return None

    user_cooldown = await cooldown_service.get_active_cooldown(
        telegram_id=message.from_user.id, cooldown_name="SNAP"
    )

    if not user_cooldown:
        logger.debug(
            "User cooldown is not active. Set new cooldown and handling command."
        )
        new_ghoul = await ghoul_service.snap_finger(telegram_id=message.from_user.id)
        change_balance = SNAP_CONFIG.award

        await user_service.plus_balance(
            telegram_id=message.from_user.id, change_balance=change_balance
        )

        await cooldown_service.set_cooldown(
            telegram_id=message.from_user.id, cooldown_type="SNAP"
        )

        caption = dialog_service.text(
            key="snap_finger_accept",
            count=str(new_ghoul.snap_count),
            money=str(change_balance),
        )

        media = await media_service.get_random_gif("snap finger")

        if not media:
            await message.reply(
                text=dialog_service.text(
                    key="snap_finger_accept",
                    count=str(new_ghoul.snap_count),
                    money=str(change_balance),
                )
            )
            return
        try:
            await message.reply_animation(
                animation=media.telegram_file_id, caption=caption
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

    cooldown_parsed = parse_seconds(
        total_seconds=int(user_cooldown.end_at - time.time())
    )

    await message.reply(
        text=dialog_service.text(
            key="snap_finger_cooldown_error",
            minutes=str(cooldown_parsed.minutes_remaining),
            seconds=str(cooldown_parsed.seconds_remaining),
        )
    )

    logger.debug("End handling command.")
