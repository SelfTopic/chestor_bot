from aiogram import BaseMiddleware, Bot
from typing import Callable, Awaitable, Dict, Any
from aiogram.types import TelegramObject, Message, CallbackQuery, Chat

import logging 

logger = logging.getLogger(__name__)

class ModeratorMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[
            [
                TelegramObject, 
                Dict[str, Any]
            ], 
            Awaitable[Any]
        ],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> None:
        logger.debug("Calling moderator middleware.")

        chat_type = "private"

        if isinstance(event, Message):
            chat_type = event.chat.type 
            

        if isinstance(event, CallbackQuery) and isinstance(event.message, Message):
            chat_type = event.message.chat.type

        if chat_type != "supergroup":

            pass # here

        bot: Bot | None = data.get("bot")

        if not bot:
            logger.error("Object of bot not found in middleware data.")
            raise RuntimeError("Object of bot not found in middleware data.")
        
        await handler(event, data)


        logger.debug("End called of moderator middleware")