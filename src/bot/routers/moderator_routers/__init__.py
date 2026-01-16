from aiogram import Router

from .set_goodbye_router import router as SetGoodbyeRouter
from .set_rules_router import router as SetRulesRouter
from .set_welcome_router import router as SetWelcomeRouter

moderator_router = Router(name=__name__)

moderator_router.include_routers(
    SetRulesRouter,
    SetGoodbyeRouter,
    SetWelcomeRouter
)

__all__ = ["moderator_router"]