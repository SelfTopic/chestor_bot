from selfrot import BaseMiddleware

from ...context import AppContext

ADMIN_STATUSES = ("administrator", "creator")


class ModeratorMiddleware(BaseMiddleware[AppContext]):
    """Как у прода: команды настройки чата — только для админа/создателя супергруппы,
    проверяется живым Bot API (get_chat_member), не по БД. Для остальных типов чата
    молчит (апдейт до хендлера не доходит)."""

    async def pre_handle(self) -> bool:
        chat = self.ctx.chat
        user = self.ctx.user
        if chat is None or user is None or chat.type != "supergroup":
            return False

        member = await self.ctx.bot.get_chat_member(chat.id, user.id)
        return member.status in ADMIN_STATUSES

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
