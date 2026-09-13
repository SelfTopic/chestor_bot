import logging
from typing import Optional

from ...database.models import Chat, User
from ..exceptions import (
    ChatMemberUpdateMessageError,
    ChatNotFoundInDatabase,
    ChatRulesError,
)
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

    async def get_random_participant(self, chat_id: int) -> Optional[User]:
        """Случайный юзер среди тех, кто хоть раз писал в этом чате (см.
        ChatParticipant) - для команды "выбери участника" (fun_router.py).
        None, если для чата ещё никого не записано (пустой чат/только что
        созданный)."""

        telegram_id = await self.chat_participant_repository.get_random_participant(
            chat_id
        )
        if telegram_id is None:
            return None

        return await self.user_repository.get(telegram_id)

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
        # Максимальная длинна сообщения в Telegram - 4096
        if len(rules) < 1 or len(rules) > 4000:
            raise ChatRulesError(
                "Кол-во символов в правилах не может быть меньше 1 и больше 4000 символов."
            )

        chat = await self.chat_repository.set_chat_rules(
            telegram_id=telegram_id, rules=rules
        )

        return chat

    async def delete_chat_rules(self, telegram_id: int) -> Chat:
        before_chat = await self.get_by_telegram_id(telegram_id=telegram_id)

        if not before_chat:
            raise ChatNotFoundInDatabase()

        if not before_chat.rules:
            raise ChatRulesError("В чате уже отсутствуют правила.")

        chat = await self.chat_repository.delete_chat_rules(telegram_id=telegram_id)

        return chat

    async def set_chat_welcome_message(
        self, telegram_id: int, welcome_message: str
    ) -> Chat:
        # Максимальная длинна сообщения в Telegram - 4096
        if len(welcome_message) < 0 or len(welcome_message) > 4000:
            raise ChatMemberUpdateMessageError(
                "Кол-во символов в приветственном сообщении не может быть меньше 1 и больше 4000 символов."
            )

        chat = await self.chat_repository.set_chat_welcome_message(
            telegram_id=telegram_id, welcome_message=welcome_message
        )

        return chat

    async def delete_chat_welcome_message(self, telegram_id: int) -> Chat:
        before_chat = await self.get_by_telegram_id(telegram_id=telegram_id)

        if not before_chat:
            raise ChatNotFoundInDatabase()

        if not before_chat.welcome_message:
            raise ChatMemberUpdateMessageError(
                "В чате уже отсутствует приветственное сообщение."
            )

        chat = await self.chat_repository.delete_chat_welcome_message(
            telegram_id=telegram_id
        )

        return chat

    async def set_chat_goodbye_message(
        self, telegram_id: int, goodbye_message: str
    ) -> Chat:
        # Максимальная длинна сообщения в Telegram - 4096
        if len(goodbye_message) < 0 or len(goodbye_message) > 4000:
            raise ChatMemberUpdateMessageError(
                "Кол-во символов в прощальном сообщении не может быть меньше 1 и больше 4000 символов."
            )

        chat = await self.chat_repository.set_chat_goodbye_message(
            telegram_id=telegram_id, goodbye_message=goodbye_message
        )

        return chat

    async def delete_chat_goodbye_message(self, telegram_id: int) -> Chat:
        before_chat = await self.get_by_telegram_id(telegram_id=telegram_id)

        if not before_chat:
            raise ChatNotFoundInDatabase()

        if not before_chat.welcome_message:
            raise ChatMemberUpdateMessageError(
                "В чате уже отсутствует прощальное сообщение."
            )

        chat = await self.chat_repository.delete_chat_goodbye_message(
            telegram_id=telegram_id
        )

        return chat
