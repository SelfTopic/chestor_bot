from aiogram import Router, F
from aiogram.types import Message 
from aiogram.filters import Command
from dependency_injector.wiring import Provide, inject
from src.database.models import Ghoul
from ..services import DialogService, UserService, GhoulService
from ..utils import calculate_kagune
from ..containers import Container
from ..types import Race
import logging 

logger = logging.getLogger(__name__)

router = Router(name=__name__)

@router.message(F.text.lower() == "распрофиль")
@router.message(Command("race_profile"))
@inject
async def profile_handler(
    message: Message,
    user_service: UserService = Provide[
        Container.user_service  
    ],
    dialog_service: DialogService = Provide[
        Container.dialog_service
    ],
    ghoul_service: GhoulService = Provide[
        Container.ghoul_service    
    ]
) -> Message:
    
    if not message.from_user:
        logger.error("User not found in message.")
        raise ValueError("User not found in message")
    
    user = await user_service.get(message.from_user.id)

    if not user:
        logger.error("User not found in database.")
        raise ValueError("User not found in database")
    
    race = user_service.race(user.race_bit)

    if not race: 
        raise 

    profile = None 

    if race == Race.GHOUL:
        profile = await ghoul_service.get(message)

    else:
        profile = Race.HUMAN

    if not profile:
        logger.error("Ghoul not found in database")
        raise ValueError("Ghoul not found in database")
    
    return_text = dialog_service.text(
        key="profile",
        name=user.full_name,
        race=race.value['name'],
        balance=user.balance    
    )
    
    if isinstance(profile, Ghoul):
        return_text = dialog_service.text(
            key="ghoul_profile",
            name=user.full_name,
            strength=profile.strength,
            snap_count=profile.snap_count,
            kagune_type=calculate_kagune(profile.kagune_type_bit)[0].value["name"],
            health=profile.health,
            max_health=profile.max_health,
            coffee_count=profile.coffee_count,
            strength_kagune=profile.kagune_strength,
            rc_count=profile.rc_money,
            regeneration=profile.regeneration,
            eat_ghouls=profile.eat_ghouls,
            eat_humans=profile.eat_humans,
            dexterity=profile.dexterity,
            speed=profile.speed,
            is_kakuja="Есть" if profile.is_kakuja else "Нет",
            level=profile.level
        )

    return await message.answer(text=return_text)

__all__ = ["router"]

