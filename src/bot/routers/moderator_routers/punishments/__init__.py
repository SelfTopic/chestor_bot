from selfrot import BaseRouter

from ....context import AppContext
from .mute import MuteHandler, MuteRepliedHandler, UnmuteHandler, UnmuteRepliedHandler


class PunishmentRouter(BaseRouter[AppContext]):
    handlers = (
        MuteRepliedHandler,
        MuteHandler,
        UnmuteRepliedHandler,
        UnmuteHandler,
    )
