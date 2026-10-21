# Роутеры по отдельности, а не одним CommonRouter: RootRouter ставит их вперемешку с
# другими областями, а порядок решает, какой хендлер сработает первым.
from .bot_router import BotRouter
from .check_balance import BalanceRouter
from .check_rules_router import CheckRulesRouter
from .fun import FunRouter
from .help_router import HelpRouter
from .profile_router import ProfileRouter
from .race_profile import RaceProfileRouter
from .rich_router import RichRouter
from .edits_router import EditsRouter
from .start_router import StartRouter
from .tops import CommonTopsRouter
from .transfer import TransferRouter

__all__ = [
    "BalanceRouter",
    "BotRouter",
    "CheckRulesRouter",
    "CommonTopsRouter",
    "FunRouter",
    "HelpRouter",
    "ProfileRouter",
    "RaceProfileRouter",
    "RichRouter",
    "EditsRouter",
    "StartRouter",
    "TransferRouter",
]
