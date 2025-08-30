from aiogram import Router 
from .routes import include_ghoul_routers

router = Router(name=__name__)

__all__ = [
    "router",
    "include_ghoul_routers"
]