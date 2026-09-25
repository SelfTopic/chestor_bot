from selfrot import BaseRouter

from ...context import AppContext
from .left_chat_member import LeftChatMemberRouter
from .new_chat_member import NewChatMemberRouter


class ChatMemberUpdateRouter(BaseRouter[AppContext]):
    routers = (NewChatMemberRouter, LeftChatMemberRouter)
