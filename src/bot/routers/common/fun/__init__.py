from selfrot import BaseRouter

from ....context import AppContext
from .handlers import (
    CalculatorHandler,
    PickHandler,
    RandomNumberHandler,
    RandomParticipantHandler,
    WhoHandler,
)


class FunRouter(BaseRouter[AppContext]):
    handlers = (
        PickHandler,
        WhoHandler,
        RandomParticipantHandler,
        RandomNumberHandler,
        CalculatorHandler,
    )
