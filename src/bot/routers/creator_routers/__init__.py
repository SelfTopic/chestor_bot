from aiogram import Router

from .media import router as MediaRouter

CreatorRouter = Router(name=__name__)
CreatorRouter.include_routers(
    MediaRouter,
)

__all__ = ["CreatorRouter"]
