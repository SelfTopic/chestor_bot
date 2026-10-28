from selfrot import BaseMiddleware
from selfrot.types import CallbackQuery, ChatMemberOwner, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.dialogs import BASE_LANGUAGE
from src.bot.repositories import (
    ChatParticipantRepository,
    ChatRepository,
    UserRepository,
)
from src.bot.types.insert import ChatInsert
from src.database.models import Chat, User

from ..context import AppContext


# Своя сразу коммитящаяся сессия, а не сессия хендлера: иначе INSERT ... ON CONFLICT держал
# бы строку User залоченной до конца хендлера.
class SyncEntitiesMiddleware(BaseMiddleware[AppContext]):
    async def pre_handle(self) -> bool:
        if self.ctx.is_background:
            return True
        event = self.ctx.event

        async with self.ctx.session_factory() as session:
            user: User | None = None
            chat: Chat | None = None
            if isinstance(event, (Message, CallbackQuery)) and event.user is not None:
                user = await UserRepository(session).upsert(
                    telegram_id=event.user.id,
                    first_name=event.user.first_name,
                    last_name=event.user.last_name,
                    username=event.user.username,
                    has_private_chat=True
                    if isinstance(event, Message) and event.chat.type == "private"
                    else None,
                )

            if isinstance(event, Message) and event.chat.type not in (
                "private",
                "channel",
            ):
                administrators = await self.ctx.bot.get_chat_administrators(
                    event.chat.id
                )
                creator = next(
                    (a for a in administrators if isinstance(a, ChatMemberOwner)),
                    administrators[0],
                )

                chat = await ChatRepository(session).upsert(
                    ChatInsert(
                        telegram_id=event.chat.id,
                        title=event.chat.title,
                        username=event.chat.username,
                        creator_id=creator.user.id,
                    )
                )
                if event.user is not None:
                    await ChatParticipantRepository(session).record_message(
                        event.chat.id, event.user.id
                    )

            self.ctx.language = await self.language(session, user, chat)
            await session.commit()

        return True

    async def language(
        self, session: AsyncSession, user: User | None, chat: Chat | None
    ) -> str:
        telegram_chat = self.ctx.chat
        if telegram_chat is not None and telegram_chat.type != "private":
            language = (
                chat.language
                if chat is not None
                else await ChatRepository(session).language(telegram_chat.id)
            )
            # Чат, чьё добавление бот не застал, говорит по-русски, как все чаты до переводов.
            return language or BASE_LANGUAGE

        if user is not None and user.language:
            return user.language
        sender = self.ctx.user
        return self.ctx.dialog_service.language_for(
            sender.language_code if sender is not None else None
        )

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
