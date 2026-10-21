from selfrot import BaseRouter

from ....context import AppContext
from .callbacks import (
    DuelPressHandler,
    NotYourDuelButtonHandler,
)
from .invite import DuelHandler, DuelRepliedHandler
from .expiry import expire_overdue_duels


class DuelRouter(BaseRouter[AppContext]):
    handlers = (
        DuelRepliedHandler,
        DuelHandler,
        DuelPressHandler,
        NotYourDuelButtonHandler,
    )


__all__ = ["DuelRouter", "expire_overdue_duels"]
