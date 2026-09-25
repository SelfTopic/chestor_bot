from selfrot import BaseRouter

from ..context import AppContext
from .common.anime import AnimeRouter
from .common.bot_router import BotRouter
from .common.check_balance import BalanceRouter
from .common.check_rules_router import CheckRulesRouter
from .common.dep_router import DepRouter
from .common.help_router import HelpRouter
from .common.profile_router import ProfileRouter
from .common.race_profile import RaceProfileRouter
from .common.role_play import RolePlayRouter
from .common.start_router import StartRouter
from .common.tops import CommonTopsRouter
from .common.transfer import TransferRouter
from .common.wordle import WordleRouter
from .chat_member_update_routers import ChatMemberUpdateRouter
from .creator_routers import CreatorRouter
from .ghoul_routers import GhoulRouter
from .moderator_routers import ModeratorRouter


class RootRouter(BaseRouter[AppContext]):
    # Порядок как в include_routers у прода: апдейт достаётся первому подошедшему.
    # ErrorRouter стал Dispatcher.on_error; ghoul_routers переносится по одному
    # файлу (пока coffee, snap, tops, upgrade_kagune).
    routers = (
        StartRouter,
        BotRouter,
        GhoulRouter,
        BalanceRouter,
        HelpRouter,
        ProfileRouter,
        RaceProfileRouter,
        ModeratorRouter,
        CheckRulesRouter,
        ChatMemberUpdateRouter,
        CreatorRouter,
        CommonTopsRouter,
        RolePlayRouter,
        WordleRouter,
        AnimeRouter,
        TransferRouter,
        DepRouter,
    )
