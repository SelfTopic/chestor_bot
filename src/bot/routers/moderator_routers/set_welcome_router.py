import logging

from aiogram import Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import ChatNotFoundInDatabase
from ...filters import Text
from ...services import ChatService

logger = logging.getLogger(__name__)

router = Router(name=__name__)

@router.message(Text("новое приветствие", startswith=True))
@inject
async def set_chat_welcome_message_handler(
    message: Message,
    chat_service: ChatService = Provide[ 
        Container.chat_service
    ]
) -> None:
    
    chat = await chat_service\
        .get_by_telegram_id(telegram_id=message.chat.id)
    
    if not chat: 
        raise ChatNotFoundInDatabase()
    
    if not message.text: 
        raise Exception("Текст сообщения пуст")
    
    welcome_message = message.text[17:]

    new_chat = await chat_service\
        .set_chat_welcome_message(telegram_id=message.chat.id, welcome_message=welcome_message)
    
    await message.answer(f"Приветственное сообщение обновлено: \n\n{new_chat.welcome_message}")