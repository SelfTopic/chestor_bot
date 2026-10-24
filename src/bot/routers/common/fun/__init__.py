from selfrot import BaseRouter

from ....context import AppContext
from .handlers import AskBotHandler, CalculatorHandler
from .quote import QuoteHandler


class FunRouter(BaseRouter[AppContext]):
    handlers = (
        AskBotHandler,
        CalculatorHandler,
        QuoteHandler,
    )
