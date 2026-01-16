from .chat_member_update_routers import UpdateChatMemberRouter
from .common.bot_router import router as BotRouter
from .common.check_balance import router as BalanceRouter
from .common.check_rules_router import router as CheckRulesRouter
from .common.error_router import router as ErrorRouter
from .common.help_router import router as HelpRouter
from .common.profile_router import router as ProfileRouter
from .common.race_profile_router import router as RaceProfileRouter
from .common.start_router import router as StartRouter
from .creator_routers import CreatorRouter
from .moderator_routers import moderator_router as ModeratorRouter

__all__ = [
    "StartRouter",
    "BotRouter",
    "ErrorRouter",
    "BalanceRouter",
    "HelpRouter",
    "ProfileRouter",
    "RaceProfileRouter",
    "CheckRulesRouter",
    "ModeratorRouter",
    "UpdateChatMemberRouter",
    "CreatorRouter",
]
