from selfrot import BaseRouter

from ....context import AppContext
from .handlers import BetHandler, CashOutHandler, HintHandler, OpenChartHandler, TargetHandler
from .screen import TelegramMachineScreen


class ChartRouter(BaseRouter[AppContext]):
    handlers = (OpenChartHandler, BetHandler, TargetHandler, CashOutHandler, HintHandler)


__all__ = ["ChartRouter", "TelegramMachineScreen"]
