from aiogram import Router, F
from aiogram.types import Message
from dependency_injector.wiring import inject, Provide 

from src.bot.services import (
    DialogService,
    GhoulService,
    CooldownService,
    UserService
)

from src.bot.containers import Container
from src.bot.utils import parse_seconds

import logging 
import random
import time

router = Router(name=__name__)

logger = logging.getLogger(__name__)

@router.message(F.text.lower() == 'щелк')
@inject
async def snap_handler(
    message: Message,
    dialog_service: DialogService = Provide[
        Container.dialog_service
    ],
    ghoul_service: GhoulService = Provide[
        Container.ghoul_service
    ],
    cooldown_service: CooldownService = Provide[
        Container.cooldown_service
    ],
    user_service: UserService = Provide[
        Container.user_service
    ]
) -> None:
    
    logger.debug("Start handling message 'щелк'.")
    
    if not message.from_user:
        logger.warning("User not found")
        return None
    
    logger.debug("Get active snap cooldown")
    user_cooldown = await cooldown_service\
        .get_active_cooldown(
            telegram_id=message.from_user.id,
            cooldown_name="SNAP"
        )
    
    if not user_cooldown:

        logger.debug("User cooldown is not active. Set new cooldown and handling command.")
        new_ghoul = await ghoul_service.snap_finger(
            telegram_id=message.from_user.id
        )
        change_balance = random.randint(500, 1000)

        await user_service.plus_balance(
            telegram_id=message.from_user.id,
            change_balance=change_balance
        )

        await cooldown_service.set_cooldown(
            telegram_id=message.from_user.id, 
            cooldown_type="SNAP"
        )
        
        await message.reply(
            text=dialog_service.text(
                key="snap_finger_accept",
                name=message.from_user.first_name or "Ghoul",
                count=str(new_ghoul.snap_count),
                money=str(change_balance)
            )    
        )

        logger.debug("Use early return pattern. End handling command.")
        return None 
    
    logger.debug("User cooldown is active. Parsing remaining time and end handling.")
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
