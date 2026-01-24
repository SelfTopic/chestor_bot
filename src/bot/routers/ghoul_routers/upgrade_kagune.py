import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import (
    CooldownService,
    DialogService,
    GhoulService,
    MediaService,
    UserService,
)
from ...utils import calculate_kagune, parse_seconds

router = Router(name=__name__)


@router.message(F.text.lower() == "растить кагуне")
@inject
async def upgrade_kagune(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
    user_service: UserService = Provide[Container.user_service],
    cooldown_service: CooldownService = Provide[Container.cooldown_service],
    media_service: MediaService = Provide[Container.media_service],
):
    if not message.from_user:
        raise ValueError("User from message not found")

    ghoul = await ghoul_service.get(message)

    if not ghoul:
        new_ghoul = await ghoul_service.register(message.from_user.id)

        if not new_ghoul.ghoul:
            raise ValueError("Ghoul is not found")

        return await message.reply(
            text=dialog_service.text(
                key="new_ghoul",
                name=message.from_user.first_name,
                kagune_type=calculate_kagune(new_ghoul.ghoul.kagune_type_bit)[0].value[
                    "name"
                ],
            )
        )

    user_cooldown = await cooldown_service.get_active_cooldown(
        telegram_id=message.from_user.id, cooldown_name="KAGUNE_UPGRADE"
    )

    if user_cooldown:
        cooldown_parsed = parse_seconds(
            total_seconds=int(user_cooldown.end_at - time.time())
        )

        return await message.reply(
            text=dialog_service.text(
                key="upgrade_kagune_cooldown_error",
                minutes=str(cooldown_parsed.minutes_remaining),
                seconds=str(cooldown_parsed.seconds_remaining),
            )
        )

    price_upgrade = ghoul_service.calculate_price_upgrade_kagune(ghoul.kagune_strength)
    user = await user_service.get(find_by=message.from_user.id)

    if not user:
        raise ValueError("User is not found")

    if user.balance < price_upgrade:
        return await message.reply(
            text=dialog_service.text(
                key="not_enough_money", money=int(price_upgrade - user.balance) + 1
            )
        )

    await user_service.minus_balance(
        telegram_id=message.from_user.id, change_balance=price_upgrade
    )

    new_ghoul = await ghoul_service.upgrade_kagune(telegram_id=message.from_user.id)

    await cooldown_service.set_cooldown(
        telegram_id=message.from_user.id, cooldown_type="KAGUNE_UPGRADE"
    )

    kagune = calculate_kagune(ghoul.kagune_type_bit)[0].value["name_english"]

    media = await media_service.get_random_gif(f"kagune {kagune}")

    text = dialog_service.text(
        key="upgrade_kagune_accept",
        name=message.from_user.first_name or "Ghoul",
        kagune_strength=str(new_ghoul.kagune_strength),
        money=str(price_upgrade),
    )

    if not media:
        await message.reply(text=text)
        return

    try:
        await message.answer_animation(animation=media.telegram_file_id, caption=text)

    except TelegramBadRequest:
        my_message = await message.answer_animation(
            animation=FSInputFile(media.path), caption=text
        )

        if not my_message.animation:
            raise

        await media_service.update_telegram_file_id(
            path=media.path, new_file_id=my_message.animation.file_id
        )
