from aiogram import Bot, Router
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import ChatNotFoundInDatabase
from ...services import ChatService, UserService
from .join_method import resolve_join_method

router = Router(name=__name__)

@router.my_chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def me_join_chat(event: ChatMemberUpdated) -> None:
    await event.answer("Пиздато конечно, что вы меня добавили. Я тупой даунский бот.")


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
@inject
async def new_chat_member(
    event: ChatMemberUpdated,
    bot: Bot,
    chat_service: ChatService = Provide[
        Container.chat_service
    ],
    user_service: UserService = Provide[Container.user_service],
) -> None:

    chat = await chat_service.get_by_telegram_id(telegram_id=event.chat.id)

    if not chat:
        raise ChatNotFoundInDatabase()

    new_member = event.new_chat_member.user

    if not new_member.is_bot:
        # User обязан существовать до записи ChatParticipant (FK) - этот
        # апдейт НЕ проходит через SyncEntitiesService (тот реагирует
        # только на Message/CallbackQuery), поэтому апсертим явно здесь.
        await user_service.upsert(new_member)
        await chat_service.record_participant_join(
            chat_id=event.chat.id,
            telegram_id=new_member.id,
            joined_at=event.date.replace(tzinfo=None),
            join_method=resolve_join_method(event),
        )

    if not chat.welcome_message:
        return None

    await event.answer(chat.welcome_message)
