from selfrot import BaseRouter

from ..context import AppContext
from .ai import AIRouter
from .arcade import ArcadeRouter
from .chat_member_update import ChatMemberUpdateRouter
from .common import (
    BalanceRouter,
    BotRouter,
    CheckRulesRouter,
    CommonTopsRouter,
    EditsRouter,
    FunRouter,
    HelpRouter,
    ProfileRouter,
    RaceProfileRouter,
    RichRouter,
    StartRouter,
    TransferRouter,
)
from .community import CommunityRouter, expire_overdue_votes
from .creator import CreatorRouter
from .ghoul import (
    GhoulRouter,
    expire_overdue_duels,
    expire_overdue_streaks,
)
from .media import MediaRouter
from .moderator import ModeratorRouter
from .role_play import RolePlayRouter
from .system import SystemRouter


class RootRouter(BaseRouter[AppContext]):
    # Порядок важен: апдейт достаётся первому подошедшему роутеру.
    routers = (
        # Раньше StartRouter: тот приветствует на любой /start, а здесь ссылки из брака.
        CommunityRouter,
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
        ArcadeRouter,
        TransferRouter,
        SystemRouter,
        # Раньше FunRouter: иначе «1000-7» посчитал бы калькулятор.
        EditsRouter,
        FunRouter,
        MediaRouter,
        # Последним: огрызается только на то, что не забрала ни одна команда.
        AIRouter,
    )


__all__ = [
    "RootRouter",
    "expire_overdue_duels",
    "expire_overdue_streaks",
    "expire_overdue_votes",
]
