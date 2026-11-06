from selfrot import BaseRouter

from ...context import AppContext
from .chart import ChartRouter, TelegramMachineScreen
from .roulette import RouletteRouter, TelegramRouletteScreen
from .storage import TelegramArcadeStorage
from .wordle import WordleRouter


class ArcadeRouter(BaseRouter[AppContext]):
    routers = (WordleRouter, RouletteRouter, ChartRouter)


__all__ = ["ArcadeRouter", "TelegramArcadeStorage", "TelegramMachineScreen", "TelegramRouletteScreen"]
