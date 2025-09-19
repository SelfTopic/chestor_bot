from aiogram import Router
from aiogram.types import Message 
from aiogram.filters import Command
from dependency_injector.wiring import Provide, inject
from ..services import DialogService
from ..containers import Container
import logging 

# Setting logger 
logger = logging.getLogger(__name__)

# Initialize a object of router 
router = Router(name=__name__)


# Handler for handling the /start command as a decorator
@router.message(Command("help"))
@inject
async def help_handler(
    message: Message,
    dialog_service: DialogService = Provide[
        Container.dialog_service
    ]
) -> Message:
    """Processes the '/help" command"""

    return await message.answer(
        text=dialog_service.text(
            key="help", 
        )    
    )

__all__ = ["router"]

