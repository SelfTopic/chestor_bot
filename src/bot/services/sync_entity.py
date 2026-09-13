import logging

from aiogram import Bot
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from ..repositories import (
    ChatParticipantRepository,
    ChatRepository,
    GhoulRepository,
    UserCooldownRepository,
    UserRepository,
)
from ..types.insert import ChatInsert
from .base import Base

logger = logging.getLogger(__name__)


class SyncEntitiesService(Base):
    def __init__(
        self,
        user_repository: UserRepository,
        ghoul_repository: GhoulRepository,
        user_cooldown_repository: UserCooldownRepository,
        chat_repository: ChatRepository,
        chat_participant_repository: ChatParticipantRepository,
    ) -> None:
        super().__init__(
            user_repository=user_repository,
            ghoul_repository=ghoul_repository,
            user_cooldown_repository=user_cooldown_repository,
            chat_repository=chat_repository,
        )
        self.chat_participant_repository = chat_participant_repository

    async def sync(self, event: TelegramObject, bot: Bot) -> None:
        logger.debug(f"Called method sync. Event type: {type(event).__name__}")

        if (
            isinstance(event, Update)
            and (
                isinstance(event.event, Message)
                or isinstance(event.event, CallbackQuery)
            )
        ) and event.event.from_user:
            logger.debug(f"Processing user sync. User ID: {event.event.from_user.id}")

            await self.user_repository.upsert(
                telegram_id=event.event.from_user.id,
                first_name=event.event.from_user.first_name,
                last_name=event.event.from_user.last_name,
                username=event.event.from_user.username,
                has_private_chat=True
                if isinstance(event.event, Message)
                and event.event.chat.type == "private"
                else None,
            )

        if (
            isinstance(event, Update) and (isinstance(event.event, Message))
        ) and event.event.chat.type not in ["private", "channel"]:
            administrators = await bot.get_chat_administrators(event.event.chat.id)
            creator = administrators[0]
            for admin in administrators:
                if admin.status == ChatMemberStatus.CREATOR:
                    creator = admin
                    break

            chat_insert_data = ChatInsert(
                telegram_id=event.event.chat.id,
                title=event.event.chat.title,
                username=event.event.chat.username,
                creator_id=creator.user.id,
            )

            await self.chat_repository.upsert(chat_insert_data)

            # "Кто вообще писал в этом чате" - самый дешёвый доступный
            # сигнал о членстве (Bot API не даёт список участников целиком
            # ни одним методом) - используется командой "выбери участника"
            # (fun_router.py). Только для реальных сообщений от юзера, не
            # для CallbackQuery (там события чата в этом же виде нет).
            if event.event.from_user:
                await self.chat_participant_repository.upsert(
                    chat_id=event.event.chat.id,
                    telegram_id=event.event.from_user.id,
                )


__all__ = ["SyncEntitiesService"]
