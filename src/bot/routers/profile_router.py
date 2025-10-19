from aiogram import Router, F
from aiogram.types import Message 
from aiogram.filters import Command
from dependency_injector.wiring import Provide, inject
from ..services import DialogService, UserService
from ..containers import Container
import logging 

logger = logging.getLogger(__name__)

router = Router(name=__name__)

@router.message(F.text.lower() == "профиль")
@router.message(Command("profile"))
@inject
async def profile_handler(
    message: Message,
    user_service: UserService = Provide[
        Container.user_service  
    ],
    dialog_service: DialogService = Provide[
        Container.dialog_service
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
        race = "Ээээ.. Пока неясно что это такое."
    else:
        race = race.value['name']

    return await message.answer(
        text=dialog_service.text(
            key="profile", 
            name=user.full_name,
            race=race,
            balance=str(user.balance)
        )    
    )

__all__ = ["router"]

