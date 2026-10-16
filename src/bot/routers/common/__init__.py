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
from .rich_router import RichRouter
from .role_play import RolePlayRouter
from .edits_router import EditsRouter
from .link_media_router import LinkMediaRouter
from .marriage import MarriageLinkRouter, MarriageRouter, expire_overdue_votes
from .music import MusicRouter
from .roast_router import RoastRouter
from .userbot_inbox import UserbotInboxRouter
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
    "RichRouter",
    "EditsRouter",
    "LinkMediaRouter",
    "MarriageLinkRouter",
    "MarriageRouter",
    "expire_overdue_votes",
    "MusicRouter",
    "RoastRouter",
    "UserbotInboxRouter",
    "RolePlayRouter",
    "StartRouter",
    "TransferRouter",
    "WordleRouter",
]
