from selfrot import BaseMiddleware
from selfrot.types import CallbackQuery, Message

from src.bot.dialogs import Dialogs

from ...context import AppContext

_GROW_KAGUNE_BYPASS = "растить кагуне"


class GhoulMiddleware(BaseMiddleware[AppContext]):
    async def pre_handle(self) -> bool:
        event = self.ctx.event
        if not isinstance(event, (Message, CallbackQuery)):
            return False

        if (
            isinstance(event, Message)
            and event.text
            and event.text.lower() == _GROW_KAGUNE_BYPASS
        ):
            return True

        user = self.ctx.user
        if user is None:
            return False

        ghoul = await self.ctx.ghoul_service.get(find_by=user.id)
        if ghoul is None:
            await event.answer(self.ctx.text(Dialogs.ghoul.not_a_ghoul()))
            return False

        if ghoul.is_dead:
            await event.answer(self.ctx.text(Dialogs.ghoul.dead()))
            return False

        return True

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
