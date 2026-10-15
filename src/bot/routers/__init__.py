from selfrot import BaseRouter

from ..context import AppContext
from .common import (
    AnimeRouter,
    BalanceRouter,
    BotRouter,
    CheckRulesRouter,
    CommonTopsRouter,
    DepRouter,
    EditsRouter,
    FunRouter,
    HelpRouter,
    LinkMediaRouter,
    MarriageLinkRouter,
    MarriageRouter,
    MusicRouter,
    ProfileRouter,
    RaceProfileRouter,
    RichRouter,
    RoastRouter,
    RolePlayRouter,
    StartRouter,
    TransferRouter,
    UserbotInboxRouter,
    WordleRouter,
)
from .chat_member_update_routers import ChatMemberUpdateRouter
from .creator_routers import CreatorRouter
from .ghoul_routers import GhoulRouter
from .moderator_routers import ModeratorRouter


class RootRouter(BaseRouter[AppContext]):
    # Порядок важен: апдейт достаётся первому подошедшему роутеру.
    routers = (
        # Раньше StartRouter: тот приветствует на любой /start, а это ссылка из брака.
        MarriageLinkRouter,
        StartRouter,
        BotRouter,
        GhoulRouter,
        BalanceRouter,
        HelpRouter,
        RichRouter,
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
        MarriageRouter,
        DepRouter,
        UserbotInboxRouter,
        # Раньше FunRouter: иначе «1000-7» посчитал бы калькулятор.
        EditsRouter,
        FunRouter,
        MusicRouter,
        LinkMediaRouter,
        # Последним: огрызается только на то, что не забрала ни одна команда.
        RoastRouter,
    )
