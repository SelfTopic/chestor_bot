from aiogram import Router, F
from aiogram.types import Message 

from dependency_injector.wiring import Provide, inject
from ..services import UserService, DialogService
from ..containers import Container
import logging 

# Setting logger 
logger = logging.getLogger(__name__)

# Initialize a object of router 
router = Router(name=__name__)


# Handler for handling the /бал command as a decorator
@router.message(F.text.lower() == 'бал')
@inject
async def start_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    dialog_service: DialogService = Provide[Container.dialog_service]
) -> Message:
    """Processes the 'бал' command"""

    # User is definitely not equal to none
    if not message.from_user:
        logger.error("User not found")
        raise ValueError("User not found")
    
    user = await user_service.get(message.from_user.id)

    if not user:
        logger.error("User not found in database")
        raise ValueError("User not found in database")
    
    logger.debug(f"User equal {user}")

    return await message.answer(
        text=dialog_service.text(
            key="check_balance", 
            balance=str(user.balance) or "undefined",
            name=user.first_name or "User"
        )    
    )

__all__ = ["router"]

