from selfrot import BaseRouter

from ..context import AppContext
from .common import (
    AnimeRouter,
    BalanceRouter,
    BotRouter,
    CheckRulesRouter,
    CommonTopsRouter,
    DepRouter,
    HelpRouter,
    ProfileRouter,
    RaceProfileRouter,
    RolePlayRouter,
    StartRouter,
    TransferRouter,
    WordleRouter,
)
from .chat_member_update_routers import ChatMemberUpdateRouter
from .creator_routers import CreatorRouter
from .ghoul_routers import GhoulRouter
from .moderator_routers import ModeratorRouter


class RootRouter(BaseRouter[AppContext]):
    # Порядок как в include_routers у прода: апдейт достаётся первому подошедшему.
    # ErrorRouter стал Dispatcher.on_error.
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
