from aiogram import Router, F
from aiogram.types import Message

from dependency_injector.wiring import inject, Provide 
from ...containers import Container
from ...services import GhoulService, DialogService

from ...utils import calculate_kagune

router = Router(name=__name__)

@router.message(F.text.lower() == "растить кагуне")
@inject
async def registration_ghoul(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    dialog_service: DialogService = Provide[Container.dialog_service]
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
    
    

    return await message.reply(
        text=dialog_service.text(
            key="raise_kagune"    
        )    
    )