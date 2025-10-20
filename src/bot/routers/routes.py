from aiogram import Dispatcher
from . import *
from .ghoul_routers import include_ghoul_routers, router as GhoulRouter
from ..middlewares import GhoulMiddleware

def include_routers(dp: Dispatcher) -> None:
    """Connects all routers on the dispatcher"""

    dp.include_routers(
        StartRouter,
        BotRouter,
        ErrorRouter,
        GhoulRouter,
        BalanceRouter,
        HelpRouter,
        ProfileRouter,
        RaceProfileRouter
    )
    
    GhoulRouter.message.middleware(GhoulMiddleware())
    GhoulRouter.callback_query.middleware(GhoulMiddleware())

    include_ghoul_routers(GhoulRouter)

__all__ = ["include_routers"]