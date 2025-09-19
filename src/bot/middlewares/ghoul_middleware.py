from aiogram import BaseMiddleware 
from aiogram.types import CallbackQuery, Message, Update, TelegramObject
from typing import Self, Any, Dict, Awaitable, Callable
from ..services import GhoulService
from ..containers import Container 
from dependency_injector.wiring import Provide
import logging 

logger = logging.getLogger(__name__)

class GhoulMiddleware(BaseMiddleware):
    """
    Middleware for managing ghoul authentication and command filtering.
    
    This middleware:
    1. Validates user registration status
    2. Allows bypass for specific commands
    3. Filters unregistered users from accessing protected handlers
    
    Flow:
    - For 'grow kagune' command: Always allow
    - For registered ghouls: Allow access
    - For unregistered ghouls: Block access
    """

    async def __call__(
        self: Self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
        ghoul_service: GhoulService = Provide[Container.ghoul_service]
    ) -> Any:
        """
        Middleware execution pipeline.
        
        Args:
            handler: Next handler in the processing chain
            event: Incoming Telegram update event
            data: Contextual data dictionary
            ghoul_service: Injected Ghoul service instance
            
        Returns:
            Result of handler execution if allowed, None otherwise
        """
        logger.debug("GhoulMiddleware processing initiated")
        
        # Validate event structure - must be Update with Message/CallbackQuery
        if ((isinstance(event, Message) or 
             isinstance(event, CallbackQuery)) and 
            event.from_user):
            
            user_id = event.from_user.id
            logger.debug(f"Processing update from user: {user_id}")
            
            # Special case: "Grow kagune" command bypass
            if (isinstance(event, Message) and event.text):
                normalized_text = event.text.lower()
                
                if normalized_text == "растить кагуне":
                    logger.info(f"Allowing 'grow kagune' command for user: {user_id}")
                    return await handler(event, data)
            
            # Check ghoul registration status
            logger.debug(f"Checking ghoul registration for user: {user_id}")
            ghoul = await ghoul_service.get(find_by=user_id)
            
            if ghoul:
                logger.info(f"Access granted: Registered ghoul ({ghoul.id})")
                return await handler(event, data)
            else:
                logger.warning(f"Access denied: Unregistered user {user_id}")
                await event.answer("Ты не гуль. Используй команду 'Растить кагуне' чтобы стать гулем.")
                return None
                
        else:
            # Skip processing for unsupported update types
            logger.debug("Skipping unsupported update type")
            return None
        
__all__ = ["GhoulMiddleware"]