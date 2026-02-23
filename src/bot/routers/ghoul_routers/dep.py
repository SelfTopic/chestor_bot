import logging
import re

from aiogram import Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.filters import Text
from src.bot.services.ghoul_game import LotteryService

router = Router(name=__name__)

logger = logging.getLogger(__name__)

DEPNUT_PATTERN = r"^депнуть\s+(\S+)\s+(\d+)$"


@router.message(Text(command="депнуть", startswith=True, pattern=DEPNUT_PATTERN))
@inject
async def depnut_handler(
    message: Message,
    lottery_service: LotteryService = Provide[Container.lottery_service],
) -> None:
    if not message.from_user or not message.text:
        return

    match = re.match(DEPNUT_PATTERN, message.text.lower())
    if not match:
        await message.reply(
            text="❌ Неверный формат команды. Используйте: депнуть <цвет> <ставка>"
        )
        return

    color_str = match.group(1)
    bet_str = match.group(2)

    try:
        chosen_color = lottery_service.parse_color(color_str=color_str)

        bet_amount = int(bet_str)

        dep_result = await lottery_service.execute(
            user_id=message.from_user.id,
            chosen_color=chosen_color,
            bet_amount=bet_amount,
        )

        await lottery_service.send_answer(message=message, dep_result=dep_result)

    except ValueError as e:
        await message.reply(text=str(e))
    except Exception as e:
        logger.error(f"Ошибка при обработке депнуть: {e}")
        await message.reply(text="❌ Произошла ошибка при обработке вашей ставки")
