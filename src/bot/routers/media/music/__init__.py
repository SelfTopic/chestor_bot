from selfrot import BaseRouter

from ....context import AppContext
from .search import SongSearchHandler
from .shazam import ShazamHandler
from .tracks import TrackPickHandler


class MusicRouter(BaseRouter[AppContext]):
    handlers = (SongSearchHandler, ShazamHandler, TrackPickHandler)


__all__ = ["MusicRouter"]
