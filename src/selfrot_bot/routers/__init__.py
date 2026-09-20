from selfrot import BaseRouter

from ..context import AppContext
from .common.bot_router import BotRouter


class RootRouter(BaseRouter[AppContext]):
    routers = (BotRouter,)
