from selfrot import BaseRouter

from ....context import AppContext
from .game import WordleGameHandler
from .start import WordleStartHandler


class WordleRouter(BaseRouter[AppContext]):
    handlers = (WordleStartHandler, WordleGameHandler)
