from selfrot import BaseRouter

from ...context import AppContext
from .coffee import CoffeeRouter
from .combat_power import CombatPowerRouter
from .duel import DuelRouter, expire_overdue_duels
from .eat_human import EatHumanRouter
from .middleware import GhoulMiddleware
from .mob_fight import MobFightRouter
from .passive_status import PassiveStatusRouter
from .quiz import QuizRouter
from .snap import SnapRouter
from .tops import TopsGhoulRouter
from .upgrade_kagune import UpgradeKaguneRouter
from .upgrade_stat import UpgradeStatRouter


class GhoulRouter(BaseRouter[AppContext]):
    middlewares = (GhoulMiddleware,)
    routers = (
        UpgradeKaguneRouter,
        SnapRouter,
        TopsGhoulRouter,
        CoffeeRouter,
        QuizRouter,
        UpgradeStatRouter,
        PassiveStatusRouter,
        EatHumanRouter,
        MobFightRouter,
        DuelRouter,
        CombatPowerRouter,
    )


__all__ = ["GhoulRouter", "expire_overdue_duels"]
