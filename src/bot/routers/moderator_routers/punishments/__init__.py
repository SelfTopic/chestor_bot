from selfrot import BaseRouter

from ....context import AppContext
from .ban import BanHandler, BanRepliedHandler, UnbanHandler, UnbanRepliedHandler
from .kick import KickHandler, KickRepliedHandler
from .mute import MuteHandler, MuteRepliedHandler, UnmuteHandler, UnmuteRepliedHandler


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
    )
