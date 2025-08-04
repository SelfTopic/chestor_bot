from aiogram import BaseMiddleware 
from aiogram.types import CallbackQuery, Message, Update, TelegramObject
from typing import Self, Any, Dict, Awaitable, Callable

import time
import logging 

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging all updates on telegram"""

    async def __call__(
        self: Self,
        handler: Callable[
            [TelegramObject, Dict[str, Any]
        ], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]  
    ) -> None:
        
        # Start time in process update
        start_time = time.time()

        await handler(event, data)

        # End time on process update
        end_time = time.time()

        # Result time process of update
        process_update_time = int((end_time - start_time)*1000)

        # Default user value (if not found)
        user_information = "Not User"

        # Getting information of user if is found 
        if (isinstance(event, Update) and 
            (
             isinstance(event.event, Message) or 
             isinstance(event.event, CallbackQuery))
            ) and event.event.from_user:
            user_information = f"Name={event.event.from_user.first_name} ID={event.event.from_user.id}"


        logger.info(f"New update on {user_information} on {process_update_time} ms. Event type is {event.__class__.__name__}")

__all__ = ["LoggingMiddleware"]