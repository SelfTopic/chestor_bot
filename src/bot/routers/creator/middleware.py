from selfrot import BaseMiddleware

from src.config import settings

from ...context import AppContext


class CreatorMiddleware(BaseMiddleware[AppContext]):
    async def pre_handle(self) -> bool:
        user = self.ctx.user
        return user is not None and user.id in settings.ADMIN_IDS

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
