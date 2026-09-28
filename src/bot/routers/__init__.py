from selfrot import BaseRouter

from ..context import AppContext
from .common import (
    AnimeRouter,
    BalanceRouter,
    BotRouter,
    CheckRulesRouter,
    CommonTopsRouter,
    DepRouter,
    FunRouter,
    HelpRouter,
    ProfileRouter,
    RaceProfileRouter,
    RoastRouter,
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
    # Порядок важен: апдейт достаётся первому подошедшему роутеру.
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
        FunRouter,
        # Последним: огрызается только на то, что не забрала ни одна команда.
        RoastRouter,
    )
