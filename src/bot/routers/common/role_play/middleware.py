from selfrot import BaseMiddleware
from selfrot.types import Message

from ....context import AppContext


class RpCommandsMiddleware(BaseMiddleware[AppContext]):
    """Прогревает кеш Role-Play команд чата перед хендлерами RolePlayRouter."""

    async def pre_handle(self) -> bool:
        event = self.ctx.event
        if isinstance(event, Message):
            await self.ctx.rp_commands_service.get_all(chat_id=event.chat.id)

        return True

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
