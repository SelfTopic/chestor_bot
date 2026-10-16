from typing import Any

from selfrot.middleware import LoggingMiddleware

from ..context import AppContext


# Задача дуэлей идёт каждую секунду: строка «Update from no user handled» на каждый её прогон
# забила бы лог, а ошибки задач и так пишет on_error.
class UpdateLoggingMiddleware(LoggingMiddleware[AppContext]):
    async def post_handle(self, exc: BaseException | None = None) -> Any:
        if self.ctx.is_background:
            return None
        return await super().post_handle(exc)
