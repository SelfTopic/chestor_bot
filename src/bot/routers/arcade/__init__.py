from selfrot import BaseRouter

from ...context import AppContext
from .dep_router import DepRouter
from .wordle import WordleRouter


class ArcadeRouter(BaseRouter[AppContext]):
    routers = (WordleRouter, DepRouter)
