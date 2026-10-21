from selfrot import BaseMiddleware

from ...context import AppContext

ADMIN_STATUSES = ("administrator", "creator")


class ModeratorMiddleware(BaseMiddleware[AppContext]):
    async def pre_handle(self) -> bool:
        chat = self.ctx.chat
        user = self.ctx.user
        if chat is None or user is None or chat.type != "supergroup":
            return False

        member = await self.ctx.bot.get_chat_member(chat.id, user.id)
        return member.status in ADMIN_STATUSES

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
