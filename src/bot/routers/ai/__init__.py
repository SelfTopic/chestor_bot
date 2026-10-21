from selfrot import BaseRouter

from ...context import AppContext
from .roast_router import RoastRouter
from .search import SearchHandler


# Свои хендлеры проверяются раньше вложенных роутеров: «бот найди» — до огрызаний,
# которые забирают всё, что осталось.
class AIRouter(BaseRouter[AppContext]):
    handlers = (SearchHandler,)
    routers = (RoastRouter,)
