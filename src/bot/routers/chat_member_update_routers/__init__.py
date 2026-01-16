from aiogram import Router

from .left_chat_member import router as LeftChatMemberRouter
from .new_chat_member import router as NewChatMemberRouter

UpdateChatMemberRouter = Router()

UpdateChatMemberRouter.include_routers(
    LeftChatMemberRouter,
    NewChatMemberRouter,
)

__all__ = ["UpdateChatMemberRouter"]