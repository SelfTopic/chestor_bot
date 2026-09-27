from datetime import datetime, timezone

from selfrot import BaseRouter
from selfrot.filter import MemberJoined
from selfrot.handlers import ChatMemberHandler, MyChatMemberHandler
from selfrot.types import ChatMemberUpdated

from src.bot.dialogs import Dialogs
from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext


class BotAddedHandler(MyChatMemberHandler[AppContext[ChatMemberUpdated]]):
    query = MemberJoined()

    async def handle(self) -> None:
        await self.ctx.my_chat_member.answer(self.ctx.text(Dialogs.moderation.bot_added()))


class NewChatMemberHandler(ChatMemberHandler[AppContext[ChatMemberUpdated]]):
    query = MemberJoined()

    async def handle(self) -> None:
        event = self.ctx.chat_member
        chat = await self.ctx.chat_service.get_by_telegram_id(event.chat.id)
        if chat is None:
            raise ChatNotFoundInDatabase()

        member = event.new_chat_member.user
        if not member.is_bot:
            await self.ctx.chat_service.record_participant_join(
                chat_id=event.chat.id,
                telegram_id=member.id,
                first_name=member.first_name,
                last_name=member.last_name,
                username=member.username,
                joined_at=datetime.fromtimestamp(event.date, timezone.utc).replace(tzinfo=None),
                join_method=self.join_method(),
            )

        if not chat.welcome_message:
            return

        await event.answer(chat.welcome_message)

    def join_method(self) -> str:
        event = self.ctx.chat_member
        # Действие совершил не сам вступающий: его добавили, остальные поля не важны.
        if event.new_chat_member.user.id != event.user.id:
            return "added_by_admin"
        if event.via_chat_folder_invite_link:
            return "chat_folder_invite_link"
        if event.invite_link is not None:
            return "invite_link"
        if event.via_join_request:
            return "join_request"
        return "self"


class NewChatMemberRouter(BaseRouter[AppContext]):
    handlers = (BotAddedHandler, NewChatMemberHandler)
