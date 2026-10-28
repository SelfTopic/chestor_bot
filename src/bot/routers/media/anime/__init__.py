from selfrot import BaseRouter

from ....context import AppContext
from .handlers import AnimeHandler, AnimeNotInLanguageHandler


class AnimeRouter(BaseRouter[AppContext]):
    handlers = (AnimeHandler, AnimeNotInLanguageHandler)
