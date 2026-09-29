from selfrot import BaseRouter

from ...context import AppContext
from .middleware import ModeratorMiddleware
from .punishments import PunishmentRouter
from .set_goodbye import SetGoodbyeHandler
from .set_rules import SetRulesHandler
from .set_welcome import SetWelcomeHandler


class ChatTextRouter(BaseRouter[AppContext]):
    middlewares = (ModeratorMiddleware,)
    handlers = (SetRulesHandler, SetWelcomeHandler, SetGoodbyeHandler)


class ModeratorRouter(BaseRouter[AppContext]):
    routers = (PunishmentRouter, ChatTextRouter)
