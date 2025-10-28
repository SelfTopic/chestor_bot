from aiogram import Router, F
from aiogram.types import Message

from dependency_injector.wiring import inject, Provide 
from ...containers import Container
from ...services import GhoulService, DialogService, UserService, CooldownService

from ...utils import calculate_kagune, parse_seconds
import time

router = Router(name=__name__)

@router.message(F.text.lower() == "растить кагуне")
@inject
async def upgrade_kagune(
    message: Message,
    ghoul_service: GhoulService = Provide[
        Container.ghoul_service
    ],
    dialog_service: DialogService = Provide[
        Container.dialog_service
    ],
    user_service: UserService = Provide[
        Container.user_service
    ],
    cooldown_service: CooldownService = Provide[
        Container.cooldown_service
    ]
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
                kagune_type=calculate_kagune(new_ghoul.ghoul.kagune_type_bit)[0].value["name"]    
            )
        )
    
    user_cooldown = await cooldown_service.get_active_cooldown(
        telegram_id=message.from_user.id,
        cooldown_name="KAGUNE_UPGRADE"
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
                key="not_enough_money",
                money=int(price_upgrade - user.balance) + 1    
            )    
        )
    
    await user_service.minus_balance(
        telegram_id=message.from_user.id,
        change_balance=price_upgrade
    )

    new_ghoul = await ghoul_service.upgrade_kagune(
        telegram_id=message.from_user.id
    )

    await cooldown_service.set_cooldown(
        telegram_id=message.from_user.id, 
        cooldown_type="KAGUNE_UPGRADE" 
    )
    
    await message.reply(
        text=dialog_service.text(
            key="upgrade_kagune_accept",
            name=message.from_user.first_name or "Ghoul",
            kagune_strength=str(new_ghoul.kagune_strength),
            money=str(price_upgrade)
        )    
    )