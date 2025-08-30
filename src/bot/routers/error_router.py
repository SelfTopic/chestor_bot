from aiogram import Router 
from aiogram.types import ErrorEvent, Message
from dependency_injector.wiring import inject, Provide 

from ..containers import Container 
from ..services import DialogService 

import logging 

logger = logging.getLogger(__name__)


router = Router(name=__name__)

@router.errors()
@inject
async def global_errors_handler(
    event: ErrorEvent, 
    dialog_service: DialogService = Provide[
        Container.dialog_service
    ]
) -> None:
    
    logger.error(f"Error: {event.exception}")

    if (isinstance(event.update.event, Message)):

        await event.update.event.answer(
            text=dialog_service.text(
                key="global_error", 
                error=str(event.exception)
            )    
        )

__all__ = ["router"]