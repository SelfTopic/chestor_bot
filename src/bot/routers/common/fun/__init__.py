from selfrot import BaseRouter

from ....context import AppContext
from .handlers import AskBotHandler, CalculatorHandler


class FunRouter(BaseRouter[AppContext]):
    handlers = (
        AskBotHandler,
        CalculatorHandler,
    )
