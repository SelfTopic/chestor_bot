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

@router.message(Text("новое прощание", startswith=True))
@inject
async def set_chat_goodbye_handler(
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
    
    goodbye_message = message.text[14:]

    new_chat = await chat_service\
        .set_chat_goodbye_message(telegram_id=message.chat.id, goodbye_message=goodbye_message)
    
    await message.answer(f"Прощальное сообщение обновлено: \n\n{new_chat.goodbye_message}")