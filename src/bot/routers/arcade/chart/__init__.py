from selfrot import BaseRouter

from ....context import AppContext
from .handlers import BetHandler, CashOutHandler, OpenChartHandler, TargetHandler
from .screen import TelegramMachineScreen
from .storage import TelegramChartStorage


class ChartRouter(BaseRouter[AppContext]):
    handlers = (OpenChartHandler, BetHandler, TargetHandler, CashOutHandler)


__all__ = ["ChartRouter", "TelegramChartStorage", "TelegramMachineScreen"]
