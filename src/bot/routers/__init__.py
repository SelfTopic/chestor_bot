from .start_router import router as StartRouter 
from .bot_router import router as BotRouter
from .error_router import router as ErrorRouter
from .check_balance import router as BalanceRouter
from .help_router import router as HelpRouter 
from .profile_router import router as ProfileRouter
from .race_profile_router import router as RaceProfileRouter 

__all__ = [
    "StartRouter",
    "BotRouter",
    "ErrorRouter",
    "BalanceRouter",
    "HelpRouter",
    "ProfileRouter",
    "RaceProfileRouter"
]