from selfrot import BaseRouter

from ...context import AppContext
from .ban import BanRouter
from .broadcast import BroadcastRouter
from .cooldown_admin import CooldownAdminRouter
from .kagune_admin import KaguneAdminRouter
from .kill import KillRouter
from .level_up import LevelUpRouter
from .media import MediaRouter
from .middleware import CreatorMiddleware
from .players_lookup import PlayersLookupRouter
from .reset import ResetRouter
from .roast_rating import RoastRatingRouter
from .stats_edits import StatsEditRouter


class CreatorRouter(BaseRouter[AppContext]):
    middlewares = (CreatorMiddleware,)
    routers = (
        MediaRouter,
        BanRouter,
        PlayersLookupRouter,
        StatsEditRouter,
        ResetRouter,
        KaguneAdminRouter,
        KillRouter,
        CooldownAdminRouter,
        BroadcastRouter,
        LevelUpRouter,
        RoastRatingRouter,
    )
