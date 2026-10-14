from selfrot import BaseRouter

from ....context import AppContext
from .handlers import AskBotHandler, CalculatorHandler
from .search import SearchHandler


class FunRouter(BaseRouter[AppContext]):
    handlers = (
        AskBotHandler,
        SearchHandler,
        CalculatorHandler,
    )
