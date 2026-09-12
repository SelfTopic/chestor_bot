from aiogram import Router

from .coffee import router as CoffeeRouter
from .dep import router as DepRouter
from .duel import router as DuelRouter
from .eat_human import router as EatHumanRouter
from .mob_fight import router as MobFightRouter
from .passive_status import router as PassiveStatusRouter
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
        DepRouter,
        QuizRouter,
        UpgradeStatRouter,
        PassiveStatusRouter,
        EatHumanRouter,
        MobFightRouter,
        DuelRouter,
    )


__all__ = ["include_ghoul_routers"]
