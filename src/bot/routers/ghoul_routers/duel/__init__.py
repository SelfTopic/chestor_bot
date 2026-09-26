"""
PvP-дуэли, порт прод-duel/:

- invite.py — шаг 1, "дуэль" (приглашение);
- callbacks.py — шаги 2, 3, 5: согласие, "всерьёз/фора", выбор победителя;
- fight.py — бой и исход, общее для нажатий и таймаутов;
- ticker.py — таймауты шагов (DuelTicker, задача уровня диспетчера);
- services.py, keyboards.py, callback_data.py.

Боевой движок и хранение (BattleService, BattleRecordService, DuelService,
ActiveBattle) берутся из прода как есть.
"""

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
