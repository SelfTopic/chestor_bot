import logging

from aiogram import F, Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import DialogService, GhoulService
from ...utils import (
    format_duration,
    get_hunger_tier,
    health_regen_per_hour,
    hours_until_full_health,
    hours_until_starved,
)

logger = logging.getLogger(__name__)

router = Router(name=__name__)


@router.message(F.text.lower() == "реген")
@inject
async def regen_status_handler(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
) -> Message:
    if not message.from_user:
        logger.error("User not found in message")
        raise ValueError("User not found in message")

    ghoul = await ghoul_service.get(message)

    if not ghoul:
        # GhoulMiddleware уже отсеивает не-гулей до хандлера - если сюда всё
        # же попали без гуля, это не "не гуль", а что-то хуже (гонка, битые
        # данные), см. тот же паттерн в GhoulService.snap_finger.
        logger.error(f"Ghoul not found for {message.from_user.id} despite GhoulMiddleware")
        raise ValueError("Ghoul not found")

    hp_per_hour = health_regen_per_hour(
        regeneration=ghoul.regeneration,
        hunger=ghoul.hunger,
        kagune_type_bit=ghoul.kagune_type_bit or 0,
        is_kakuja=ghoul.is_kakuja,
    )
    hours_left = hours_until_full_health(ghoul.health, ghoul.max_health, hp_per_hour)

    if hours_left == 0.0:
        time_left = "Уже полностью здоров(а)."
    elif hours_left is None:
        time_left = "При текущей скорости регенерации здоровье само не восстановится."
    else:
        time_left = f"До полного здоровья: {format_duration(int(hours_left * 3600))}"

    return await message.answer(
        text=dialog_service.text(
            key="regen_status",
            health=ghoul.health,
            max_health=ghoul.max_health,
            hp_per_hour=round(hp_per_hour, 2),
            time_left=time_left,
        )
    )


@router.message(F.text.lower() == "голод")
@inject
async def hunger_status_handler(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
) -> Message:
    if not message.from_user:
        logger.error("User not found in message")
        raise ValueError("User not found in message")

    ghoul = await ghoul_service.get(message)

    if not ghoul:
        logger.error(f"Ghoul not found for {message.from_user.id} despite GhoulMiddleware")
        raise ValueError("Ghoul not found")

    hours_left = hours_until_starved(ghoul.hunger, ghoul.is_kakuja)
    tier = get_hunger_tier(ghoul.hunger)

    if hours_left <= 0:
        time_left = "Голод уже на нуле."
    else:
        time_left = f"До истощения: {format_duration(int(hours_left * 3600))}"

    return await message.answer(
        text=dialog_service.text(
            key="hunger_status",
            hunger=ghoul.hunger,
            tier=tier.name,
            time_left=time_left,
        )
    )


__all__ = ["router"]
