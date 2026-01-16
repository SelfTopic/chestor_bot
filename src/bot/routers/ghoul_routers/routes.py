from aiogram import Router

from .snap import router as SnapFingerRouter
from .tops import router as TopsGhoulRouter
from .upgrade_kagune import router as RaiseKaguneRouter


def include_ghoul_routers(rt: Router) -> None:
    rt.include_routers(RaiseKaguneRouter, SnapFingerRouter, TopsGhoulRouter)


__all__ = ["include_ghoul_routers"]
