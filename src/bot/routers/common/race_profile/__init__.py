from selfrot import BaseRouter

from ....context import AppContext
from .kagune import KaguneInfoHandler
from .profile import RaceProfileHandler


class RaceProfileRouter(BaseRouter[AppContext]):
    handlers = (KaguneInfoHandler, RaceProfileHandler)
