from selfrot import BaseRouter

from ....context import AppContext
from .handlers import BetHandler, CashOutHandler, HintHandler, OpenChartHandler, TargetHandler
from .screen import TelegramMachineScreen
from .storage import TelegramChartStorage


class ChartRouter(BaseRouter[AppContext]):
    handlers = (OpenChartHandler, BetHandler, TargetHandler, CashOutHandler, HintHandler)


__all__ = ["ChartRouter", "TelegramChartStorage", "TelegramMachineScreen"]
