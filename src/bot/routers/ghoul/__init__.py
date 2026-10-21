from selfrot import BaseRouter

from ...context import AppContext
from .coffee import CoffeeRouter
from .combat_power import CombatPowerRouter
from .duel import DuelRouter, expire_overdue_duels
from .eat_human import EatHumanRouter
from .evolution import EvolutionRouter
from .middleware import GhoulMiddleware
from .mob_fight import MobFightRouter
from .passive_status import PassiveStatusRouter
from .profile import GhoulProfileRouter
from .promo import PromoRouter
from .quiz import QuizRouter, expire_overdue_streaks
from .snap import SnapRouter
from .subscription import ChannelSubscriptionMiddleware, SubscriptionCheckRouter
from .tops import TopsGhoulRouter
from .upgrade_kagune import RegistrationRouter, UpgradeKaguneRouter
from .upgrade_stat import UpgradeStatRouter


# Без проверок: кнопку «я подписался» жмут как раз те, кого подписка не пускает.
class GhoulOpenRouter(BaseRouter[AppContext]):
    routers = (SubscriptionCheckRouter, GhoulProfileRouter)


class GhoulAliveRouter(BaseRouter[AppContext]):
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
        EvolutionRouter,
        MobFightRouter,
        DuelRouter,
        CombatPowerRouter,
        PromoRouter,
    )


# Регистрация раньше живых: «растить кагуне» без гуля или с мёртвым — рождение, а не прокачка.
class GhoulSubscribedRouter(BaseRouter[AppContext]):
    middlewares = (ChannelSubscriptionMiddleware,)
    routers = (RegistrationRouter, GhoulAliveRouter)


class GhoulRouter(BaseRouter[AppContext]):
    routers = (GhoulOpenRouter, GhoulSubscribedRouter)


__all__ = [
    "GhoulRouter",
    "expire_overdue_duels",
    "expire_overdue_streaks",
]
