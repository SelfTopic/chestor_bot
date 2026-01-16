from aiogram import Router

from .snap import router as SnapFingerRouter
from .upgrade_kagune import router as RaiseKaguneRouter


def include_ghoul_routers(rt: Router) -> None:

    rt.include_routers(
        RaiseKaguneRouter,
        SnapFingerRouter
    )

__all__ = ["include_ghoul_routers"]