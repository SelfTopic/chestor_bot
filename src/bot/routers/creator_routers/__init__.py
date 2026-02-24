from aiogram import Router

from .ban import router as BanRouter
from .broadcast import router as BroadcastRouter
from .media import router as MediaRouter
from .players_lookup import router as PlayersLookupRouter
from .reset import router as ResetRouter
from .stats_edits import router as StatsEditRouter

CreatorRouter = Router(name=__name__)
CreatorRouter.include_routers(
    MediaRouter,
    BanRouter,
    PlayersLookupRouter,
    StatsEditRouter,
    ResetRouter,
    BroadcastRouter,
)

__all__ = ["CreatorRouter"]
