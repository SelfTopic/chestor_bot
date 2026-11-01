from selfrot import BaseRouter

from ....context import AppContext
from .ban import BanHandler, BanRepliedHandler, UnbanHandler, UnbanRepliedHandler
from .kick import KickHandler, KickRepliedHandler
from .lists import (
    BanListHandler,
    BanListPressHandler,
    KickListHandler,
    KickListPressHandler,
    MuteListHandler,
    MuteListPressHandler,
    WarnListHandler,
    WarnListPressHandler,
)
from .mute import MuteHandler, MuteRepliedHandler, UnmuteHandler, UnmuteRepliedHandler
from .warn import UnwarnHandler, UnwarnRepliedHandler, WarnHandler, WarnRepliedHandler
from .warns_list import OwnWarnsHandler, WarnsHandler, WarnsRepliedHandler


class PunishmentRouter(BaseRouter[AppContext]):
    handlers = (
        MuteRepliedHandler,
        MuteHandler,
        UnmuteRepliedHandler,
        UnmuteHandler,
        BanRepliedHandler,
        BanHandler,
        UnbanRepliedHandler,
        UnbanHandler,
        KickRepliedHandler,
        KickHandler,
        WarnRepliedHandler,
        WarnHandler,
        UnwarnRepliedHandler,
        UnwarnHandler,
        # Свои варны — раньше чужих: «варны» без цели админу иначе ответил бы подсказкой.
        OwnWarnsHandler,
        WarnsRepliedHandler,
        WarnsHandler,
        MuteListHandler,
        BanListHandler,
        WarnListHandler,
        KickListHandler,
        MuteListPressHandler,
        BanListPressHandler,
        WarnListPressHandler,
        KickListPressHandler,
    )
