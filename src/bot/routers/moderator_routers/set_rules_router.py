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

@router.message(Text("новые правила", startswith=True))
@inject
async def set_chat_rules_handler(
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
    
    rules = message.text[13:]

    new_chat = await chat_service\
        .set_chat_rules(telegram_id=message.chat.id, rules=rules)
    
    await message.answer(f"Правила чата обновлены: \n\n{new_chat.rules}")