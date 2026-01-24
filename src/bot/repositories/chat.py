import logging
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Chat
from ..exceptions import ChatNotFoundInDatabase
from ..types.insert import ChatInsert
from .base import Base

logger = logging.getLogger(__name__)


class ChatRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, chat_insert_data: ChatInsert) -> Chat:
        stmt = (
            insert(Chat)
            .values(
                telegram_id=chat_insert_data.telegram_id,
                title=chat_insert_data.title,
                username=chat_insert_data.username,
                creator_id=chat_insert_data.creator_id,
            )
            .on_conflict_do_update(
                index_elements=["telegram_id"],
                set_={
                    "title": chat_insert_data.title,
                    "username": chat_insert_data.username,
                    "creator_id": chat_insert_data.creator_id,
                },
            )
            .returning(Chat)
        )

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat

    async def get_chat_by_telegram_id(self, telegram_id: int) -> Optional[Chat]:
        stmt = select(Chat).where(Chat.telegram_id == telegram_id)

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat

    async def get_chat_by_id(self, chat_id: int) -> Optional[Chat]:
        stmt = select(Chat).where(Chat.id == chat_id)

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat

    async def set_chat_rules(self, telegram_id: int, rules: str) -> Chat:
        stmt = (
            update(Chat)
            .where(Chat.telegram_id == telegram_id)
            .values(rules=rules)
            .returning(Chat)
        )

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat

    async def delete_chat_rules(self, telegram_id: int) -> Chat:
        stmt = (
            update(Chat)
            .where(Chat.telegram_id == telegram_id)
            .values(rules=None)
            .returning(Chat)
        )

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat

    async def set_chat_welcome_message(
        self, telegram_id: int, welcome_message: str
    ) -> Chat:
        stmt = (
            update(Chat)
            .where(Chat.telegram_id == telegram_id)
            .values(welcome_message=welcome_message)
            .returning(Chat)
        )

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat

    async def delete_chat_welcome_message(self, telegram_id: int) -> Chat:
        stmt = (
            update(Chat)
            .where(Chat.telegram_id == telegram_id)
            .values(welcome_message=None)
            .returning(Chat)
        )

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat

    async def set_chat_goodbye_message(
        self, telegram_id: int, goodbye_message: str
    ) -> Chat:
        stmt = (
            update(Chat)
            .where(Chat.telegram_id == telegram_id)
            .values(goodbye_message=goodbye_message)
            .returning(Chat)
        )

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat

    async def delete_chat_goodbye_message(self, telegram_id: int) -> Chat:
        stmt = (
            update(Chat)
            .where(Chat.telegram_id == telegram_id)
            .values(goodbye_message=None)
            .returning(Chat)
        )

        chat = await self.session.scalar(stmt)

        if not chat:
            raise ChatNotFoundInDatabase()

        return chat
