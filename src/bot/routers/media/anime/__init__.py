from selfrot import BaseRouter

from ....context import AppContext
from .handlers import AnimeHandler


class AnimeRouter(BaseRouter[AppContext]):
    handlers = (AnimeHandler,)
