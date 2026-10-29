from selfrot import BaseRouter

from ..context import AppContext
from .ai import AIRouter
from .arcade import ArcadeRouter
from .chat_member_update import ChatMemberUpdateRouter
from .common import CommonRouter, reward_cult_hashtags
from .community import CommunityRouter, expire_overdue_votes
from .creator import CreatorRouter
from .ghoul import GhoulRouter, expire_overdue_duels, expire_overdue_streaks
from .media import MediaRouter
from .moderator import ModeratorRouter
from .role_play import RolePlayRouter
from .system import SystemRouter


class RootRouter(BaseRouter[AppContext]):
    # Порядок важен: апдейт достаётся первому подошедшему роутеру.
    routers = (
        # Раньше Common: «/start» там приветствует на любой текст после команды, а здесь
        # ссылки из брака.
        CommunityRouter,
        # Раньше Common: «распрофиль» в Common отвечает человеческой карточкой кому угодно.
        GhoulRouter,
        # Явные команды с ограниченным доступом раньше пассивных: калькулятор в Common
        # ловит любую арифметику, Media — любую ссылку.
        ModeratorRouter,
        CreatorRouter,
        ChatMemberUpdateRouter,
        CommonRouter,
        # После Common: свои команды чата не перекрывают встроенные.
        RolePlayRouter,
        ArcadeRouter,
        SystemRouter,
        MediaRouter,
        # Последним: огрызается только на то, что не забрала ни одна команда.
        AIRouter,
    )


__all__ = [
    "RootRouter",
    "expire_overdue_duels",
    "expire_overdue_streaks",
    "expire_overdue_votes",
    "reward_cult_hashtags",
]
