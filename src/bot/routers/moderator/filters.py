from typing import Any

from selfrot import BaseContext
from selfrot.filter import BaseFilter
from selfrot.types import Message

from ...context import AppContext


def is_anonymous_admin(message: Message) -> bool:
    return message.sender_chat is not None and message.sender_chat.id == message.chat.id


class FromChatAdmin(BaseFilter[AppContext[Any]]):
    async def check(self, ctx: BaseContext[Any]) -> bool:
        assert isinstance(ctx, AppContext)

        message = ctx.event
        if not isinstance(message, Message) or message.chat.type != "supergroup":
            return False
        if is_anonymous_admin(message):
            return True
        if message.user is None:
            return False

        administrators = await ctx.chat_administrators()
        return any(admin.user.id == message.user.id for admin in administrators)


class InGroup(BaseFilter[AppContext[Any]]):
    async def check(self, ctx: BaseContext[Any]) -> bool:
        chat = ctx.chat
        return chat is not None and chat.type in ("group", "supergroup")
