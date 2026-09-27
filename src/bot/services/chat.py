import logging
from datetime import datetime
from typing import Optional

from ...database.models import Chat, User
from ..exceptions import ChatTextLengthError
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


class ChatService(Base):
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

    async def random_participant(self, chat_id: int) -> Optional[User]:
        return await self.chat_participant_repository.random_participant(chat_id)

    async def record_participant_join(
        self,
        chat_id: int,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str],
        username: Optional[str],
        joined_at: datetime,
        join_method: str,
    ) -> None:
        # Вход в чат не проходит через SyncEntitiesMiddleware, а участник ссылается на User.
        await self.user_repository.upsert(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        await self.chat_participant_repository.record_join(
            chat_id=chat_id,
            telegram_id=telegram_id,
            joined_at=joined_at,
            join_method=join_method,
        )

    async def remove_participant(self, chat_id: int, telegram_id: int) -> None:
        await self.chat_participant_repository.remove(chat_id, telegram_id)

    async def upsert(
        self,
        telegram_id: int,
        title: Optional[str],
        username: Optional[str],
        creator_id: Optional[int],
    ) -> Optional[Chat]:
        insert_data = ChatInsert(
            telegram_id=telegram_id,
            title=title,
            username=username,
            creator_id=creator_id,
        )

        user = await self.chat_repository.upsert(insert_data)

        return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Chat]:
        chat = await self.chat_repository.get_chat_by_telegram_id(
            telegram_id=telegram_id
        )

        return chat

    async def set_chat_rules(self, telegram_id: int, rules: str) -> Chat:
        if len(rules) < 1 or len(rules) > 4000:
            raise ChatTextLengthError("rules")

        chat = await self.chat_repository.set_chat_rules(
            telegram_id=telegram_id, rules=rules
        )

        return chat

    async def set_chat_welcome_message(
        self, telegram_id: int, welcome_message: str
    ) -> Chat:
        if len(welcome_message) < 0 or len(welcome_message) > 4000:
            raise ChatTextLengthError("welcome")

        chat = await self.chat_repository.set_chat_welcome_message(
            telegram_id=telegram_id, welcome_message=welcome_message
        )

        return chat

    async def set_chat_goodbye_message(
        self, telegram_id: int, goodbye_message: str
    ) -> Chat:
        if len(goodbye_message) < 0 or len(goodbye_message) > 4000:
            raise ChatTextLengthError("goodbye")

        chat = await self.chat_repository.set_chat_goodbye_message(
            telegram_id=telegram_id, goodbye_message=goodbye_message
        )

        return chat
