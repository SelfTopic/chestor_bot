from aiogram import Dispatcher

from ..middlewares import (
    CreatorMiddleware,
    GhoulMiddleware,
    ModeratorMiddleware,
    RpCommandsMiddleware,
)
from . import *
from .ghoul_routers import include_ghoul_routers
from .ghoul_routers import router as GhoulRouter


def include_routers(dp: Dispatcher) -> None:
    ModeratorRouter.message.middleware(ModeratorMiddleware())
    ModeratorRouter.callback_query.middleware(ModeratorMiddleware())

    GhoulRouter.message.middleware(GhoulMiddleware())
    GhoulRouter.callback_query.middleware(GhoulMiddleware())

    CreatorRouter.message.middleware(CreatorMiddleware())
    CreatorRouter.callback_query.middleware(CreatorMiddleware())

    RolePlayRouter.message.middleware(RpCommandsMiddleware())

    dp.include_routers(
        StartRouter,
        BotRouter,
        ErrorRouter,
        GhoulRouter,
        BalanceRouter,
        HelpRouter,
        ProfileRouter,
        RaceProfileRouter,
        ModeratorRouter,
        CheckRulesRouter,
        UpdateChatMemberRouter,
        CreatorRouter,
        CommonTopsRouter,
        RolePlayRouter,
    )

    include_ghoul_routers(GhoulRouter)


__all__ = ["include_routers"]
