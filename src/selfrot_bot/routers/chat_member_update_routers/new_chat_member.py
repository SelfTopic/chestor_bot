from selfrot import BaseRouter
from selfrot.filter import MemberJoined
from selfrot.handlers import ChatMemberHandler, MyChatMemberHandler
from selfrot.types import ChatMemberUpdated

from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext


class BotAddedHandler(MyChatMemberHandler[AppContext[ChatMemberUpdated]]):
    """Бота добавили в чат."""

    query = MemberJoined()

    async def handle(self) -> None:
        await self.ctx.my_chat_member.answer(
            "Пиздато конечно, что вы меня добавили. Я тупой даунский бот."
        )


class NewChatMemberHandler(ChatMemberHandler[AppContext[ChatMemberUpdated]]):
    """Реальный участник вошёл в чат. Приветствие только если задано для чата;
    сам чат может ещё не существовать в БД, если это первый апдейт о нём вообще
    (SyncEntitiesMiddleware заводит запись на Message/CallbackQuery, не на
    ChatMemberUpdated) — как у прода, тогда ChatNotFoundInDatabase падает в
    Dispatcher.on_error, а не гасится тут."""

    query = MemberJoined()

    async def handle(self) -> None:
        event = self.ctx.chat_member
        chat = await self.ctx.chat_service.get_by_telegram_id(event.chat.id)
        if chat is None:
            raise ChatNotFoundInDatabase()

        if not chat.welcome_message:
            return

        await event.answer(chat.welcome_message)


class NewChatMemberRouter(BaseRouter[AppContext]):
    handlers = (BotAddedHandler, NewChatMemberHandler)
