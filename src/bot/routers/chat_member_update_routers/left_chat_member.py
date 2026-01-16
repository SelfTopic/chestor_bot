from aiogram import Router
from aiogram.filters import LEAVE_TRANSITION, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import ChatNotFoundInDatabase
from ...services import ChatService

router = Router(name=__name__)

@router.my_chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def me_leave_chat(event: ChatMemberUpdated) -> None:
    # TODO - добавить уведомление об изгании из чата
    pass
    

@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
@inject
async def left_chat_member(
    event: ChatMemberUpdated,
    chat_service: ChatService = Provide[
        Container.chat_service
    ]
) -> None:
    
    chat = await chat_service.get_by_telegram_id(telegram_id=event.chat.id)

    if not chat: 
        raise ChatNotFoundInDatabase()
    
    if not chat.goodbye_message:
        return None 
    
    await event.answer(chat.goodbye_message)