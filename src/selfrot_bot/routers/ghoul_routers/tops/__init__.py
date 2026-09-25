from selfrot import BaseRouter

from ....context import AppContext
from .top_kagune import TopKaguneRouter
from .top_snap import TopSnapRouter


class TopsGhoulRouter(BaseRouter[AppContext]):
    routers = (TopSnapRouter, TopKaguneRouter)
