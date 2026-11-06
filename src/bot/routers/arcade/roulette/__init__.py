from selfrot import BaseRouter

from ....context import AppContext
from .handlers import AmountHandler, ColorHandler, HintHandler, OpenRouletteHandler, SpinHandler
from .screen import TelegramRouletteScreen


class RouletteRouter(BaseRouter[AppContext]):
    handlers = (OpenRouletteHandler, ColorHandler, AmountHandler, SpinHandler, HintHandler)


__all__ = ["RouletteRouter", "TelegramRouletteScreen"]
