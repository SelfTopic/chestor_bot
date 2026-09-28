# Роутеры по отдельности, а не одним CommonRouter: RootRouter ставит их вперемешку с
# другими областями, а порядок решает, какой хендлер сработает первым.
from .anime import AnimeRouter
from .bot_router import BotRouter
from .check_balance import BalanceRouter
from .check_rules_router import CheckRulesRouter
from .dep_router import DepRouter
from .fun import FunRouter
from .help_router import HelpRouter
from .profile_router import ProfileRouter
from .race_profile import RaceProfileRouter
from .role_play import RolePlayRouter
from .roast_router import RoastRouter
from .start_router import StartRouter
from .tops import CommonTopsRouter
from .transfer import TransferRouter
from .wordle import WordleRouter

__all__ = [
    "AnimeRouter",
    "BalanceRouter",
    "BotRouter",
    "CheckRulesRouter",
    "CommonTopsRouter",
    "DepRouter",
    "FunRouter",
    "HelpRouter",
    "ProfileRouter",
    "RaceProfileRouter",
    "RoastRouter",
    "RolePlayRouter",
    "StartRouter",
    "TransferRouter",
    "WordleRouter",
]
