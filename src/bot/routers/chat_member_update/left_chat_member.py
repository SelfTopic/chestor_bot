from selfrot import BaseRouter
from selfrot.filter import MemberLeft
from selfrot.handlers import ChatMemberHandler
from selfrot.types import ChatMemberUpdated

from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext


class LeftChatMemberHandler(ChatMemberHandler[AppContext[ChatMemberUpdated]]):
    query = MemberLeft()

    async def handle(self) -> None:
        event = self.ctx.chat_member
        chat = await self.ctx.chat_service.get_by_telegram_id(event.chat.id)
        if chat is None:
            raise ChatNotFoundInDatabase()

        await self.ctx.chat_service.remove_participant(
            event.chat.id, event.new_chat_member.user.id
        )

        if not chat.goodbye_message:
            return

        await event.answer(chat.goodbye_message)


class LeftChatMemberRouter(BaseRouter[AppContext]):
    handlers = (LeftChatMemberHandler,)
