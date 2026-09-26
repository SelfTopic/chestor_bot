from selfrot import BaseRouter
from selfrot.filter import MemberLeft
from selfrot.handlers import ChatMemberHandler
from selfrot.types import ChatMemberUpdated

from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext

# Прод держит тут ещё my_chat_member-хендлер на изгнание бота — пустой `pass` с
# TODO «добавить уведомление об изгнании из чата», то есть намеренная заглушка без
# поведения. Она не даёт ничего понаблюдать, а my_chat_member и так запрашивается
# библиотекой из-за BotAddedHandler (new_chat_member.py), так что здесь она не
# перенесена — TODO остаётся TODO.


class LeftChatMemberHandler(ChatMemberHandler[AppContext[ChatMemberUpdated]]):
    """Реальный участник вышел из чата. См. NewChatMemberHandler про
    ChatNotFoundInDatabase, если чата ещё нет в БД."""

    query = MemberLeft()

    async def handle(self) -> None:
        event = self.ctx.chat_member
        chat = await self.ctx.chat_service.get_by_telegram_id(event.chat.id)
        if chat is None:
            raise ChatNotFoundInDatabase()

        if not chat.goodbye_message:
            return

        await event.answer(chat.goodbye_message)


class LeftChatMemberRouter(BaseRouter[AppContext]):
    handlers = (LeftChatMemberHandler,)
