from selfrot import BaseRouter

from ....context import AppContext
from .callbacks import (
    DuelPressHandler,
    MalformedDuelButtonHandler,
    NotYourDuelButtonHandler,
)
from .invite import DuelHandler, DuelRepliedHandler
from .ticker import DuelTicker


class DuelRouter(BaseRouter[AppContext]):
    handlers = (
        DuelRepliedHandler,
        DuelHandler,
        DuelPressHandler,
        NotYourDuelButtonHandler,
        MalformedDuelButtonHandler,
    )


__all__ = ["DuelRouter", "DuelTicker"]
