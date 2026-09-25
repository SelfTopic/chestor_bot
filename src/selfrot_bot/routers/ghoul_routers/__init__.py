from selfrot import BaseRouter

from ...context import AppContext
from .coffee import CoffeeRouter
from .combat_power import CombatPowerRouter
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
    """Игровые команды за GhoulMiddleware: без гуля (кроме "растить кагуне") и
    мёртвым гулям доступ закрыт. Портируется по одному файлу; порядок — как в
    прод-include_ghoul_routers (боевые — eat_human/mob_fight/duel — последними)."""

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
        CombatPowerRouter,
    )
