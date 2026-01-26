import logging
import time

from aiogram import F, Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.services.ghoul_game import CoffeeService

from ...utils import parse_seconds

router = Router(name=__name__)

logger = logging.getLogger(__name__)


@router.message(F.text.lower() == "пить кофе")
@inject
async def coffee_handler(
    message: Message, coffee_service: CoffeeService = Provide[Container.coffee_service]
) -> None:
    if not message.from_user:
        raise

    if not await coffee_service.check_snap_limit(message=message):
        return

    cooldown_info = await coffee_service.execute_cooldown(user_id=message.from_user.id)

    if cooldown_info:
        cooldown_remaining = parse_seconds(
            total_seconds=int(cooldown_info.end_at - time.time())
        )

        await message.reply(
            text=coffee_service.dialog_service.text(
                key="coffee_cooldown_error",
                hours=cooldown_remaining.hours_remaining,
                minutes=cooldown_remaining.minutes_remaining,
                seconds=cooldown_remaining.seconds_remaining,
            )
        )
        return

    coffee_result = await coffee_service.execute(user_id=message.from_user.id)

    await coffee_service.send_answer(message=message, coffee_result=coffee_result)
