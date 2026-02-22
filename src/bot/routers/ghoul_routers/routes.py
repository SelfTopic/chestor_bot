from aiogram import Router

from .coffee import router as CoffeeRouter
from .quiz import router as QuizRouter
from .snap import router as SnapFingerRouter
from .tops import router as TopsGhoulRouter
from .upgrade_kagune import router as RaiseKaguneRouter
from .upgrade_stat import router as UpgradeStatRouter


def include_ghoul_routers(rt: Router) -> None:
    rt.include_routers(
        RaiseKaguneRouter,
        SnapFingerRouter,
        TopsGhoulRouter,
        CoffeeRouter,
        QuizRouter,
        UpgradeStatRouter,
    )


__all__ = ["include_ghoul_routers"]
