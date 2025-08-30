from aiogram import Router, F
from aiogram.types import Message 

from dependency_injector.wiring import Provide, inject
from ..services import DialogService
from ..containers import Container
import logging 

# Setting logger 
logger = logging.getLogger(__name__)

# Initialize a object of router 
router = Router(name=__name__)


# Handler for handling the /start command as a decorator
@router.message(F.text.lower() == "бот")
@inject
async def bot_handler(
    message: Message,
    dialog_service: DialogService = Provide[
        Container.dialog_service
    ]
) -> Message:
    """Processes the 'бот" command"""

    return await message.answer(
        text=dialog_service.random(
            key="bot", 
        )    
    )

__all__ = ["router"]

