from selfrot import BaseRouter

from ...context import AppContext
from .bot_router import BotRouter
from .check_balance import BalanceRouter
from .check_rules_router import CheckRulesRouter
from .edits_router import EditsRouter
from .fun import FunRouter
from .help_router import HelpRouter
from .language_router import LanguageRouter
from .profile_router import ProfileRouter
from .race_profile import RaceProfileRouter
from .rich_router import RichRouter
from .start_router import StartRouter
from .tops import CommonTopsRouter
from .transfer import TransferRouter


class CommonRouter(BaseRouter[AppContext]):
    routers = (
        StartRouter,
        BotRouter,
        BalanceRouter,
        HelpRouter,
        LanguageRouter,
        RichRouter,
        ProfileRouter,
        RaceProfileRouter,
        CheckRulesRouter,
        CommonTopsRouter,
        TransferRouter,
        # Раньше FunRouter: иначе «1000-7» посчитал бы калькулятор.
        EditsRouter,
        FunRouter,
    )
