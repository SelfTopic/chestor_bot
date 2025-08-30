from aiogram import Router, F
from aiogram.types import Message
from dependency_injector.wiring import inject, Provide 

from src.bot.services import (
    DialogService,
    GhoulService,
    CooldownService
)

from src.bot.containers import Container
from src.bot.utils import parse_seconds

import logging 
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
    ]
) -> None:
    
    if not message.from_user:
        logger.error("User not found")
        raise ValueError("User not found")
    
    snap_cooldown = await cooldown_service\
        .set_cooldown(
            telegram_id=message.from_user.id,
            cooldown_type="SNAP" 
        )

    is_cooldown = await cooldown_service\
        .is_end_cooldown(
            telegram_id=message.from_user.id,
            cooldown_type="SNAP"    
        )
    
    if is_cooldown:

        new_ghoul = await ghoul_service.snap_finger(
            telegram_id=message.from_user.id
        )
        await cooldown_service.reset_cooldown(
            telegram_id=message.from_user.id, 
            cooldown_type="SNAP"
        )
        
        await message.reply(
            text=dialog_service.text(
                key="snap_finger_accept",
                name=message.from_user.first_name or "Ghoul",
                count=str(new_ghoul.snap_count)
            )    
        )

        return None 
    
    cooldown_parsed = parse_seconds(
        total_seconds=int(snap_cooldown.end_at - time.time())
    )

    await message.reply(
        text=dialog_service.text(
            key="snap_finger_cooldown_error",
            minutes=str(cooldown_parsed.minutes_remaining),
            seconds=str(cooldown_parsed.seconds_remaining)
        )    
    ) 
    
