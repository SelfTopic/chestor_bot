from selfrot import BaseRouter

from ...context import AppContext
from .anime import AnimeRouter
from .link_media_router import LinkMediaRouter
from .music import MusicRouter


class MediaRouter(BaseRouter[AppContext]):
    routers = (AnimeRouter, MusicRouter, LinkMediaRouter)
