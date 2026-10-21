from selfrot import BaseRouter

from ...context import AppContext
from .userbot_inbox import UserbotInboxRouter


class SystemRouter(BaseRouter[AppContext]):
    routers = (UserbotInboxRouter,)
