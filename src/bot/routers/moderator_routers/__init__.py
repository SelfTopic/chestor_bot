from selfrot import BaseRouter

from ...context import AppContext
from .middleware import ModeratorMiddleware
from .set_goodbye import SetGoodbyeHandler
from .set_rules import SetRulesHandler
from .set_welcome import SetWelcomeHandler


class ModeratorRouter(BaseRouter[AppContext]):
    """Настройка чата (новые правила/приветствие/прощание) — только для админа и
    создателя супергруппы (ModeratorMiddleware, живая проверка через Bot API)."""

    middlewares = (ModeratorMiddleware,)
    handlers = (SetRulesHandler, SetWelcomeHandler, SetGoodbyeHandler)
