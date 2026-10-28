from selfrot import BaseRouter

from ....context import AppContext
from .handlers import AskBotHandler, CalculatorHandler
from .quote import QuoteHandler, QuoteNotInLanguageHandler


class FunRouter(BaseRouter[AppContext]):
    handlers = (
        AskBotHandler,
        CalculatorHandler,
        QuoteHandler,
        QuoteNotInLanguageHandler,
    )
