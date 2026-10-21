from selfrot import BaseRouter

from ....context import AppContext
from .give import GiveKaguneHandler, GiveKaguneRepliedHandler
from .remove import RemoveKaguneHandler, RemoveKaguneRepliedHandler


class KaguneAdminRouter(BaseRouter[AppContext]):
    handlers = (
        GiveKaguneRepliedHandler,
        GiveKaguneHandler,
        RemoveKaguneRepliedHandler,
        RemoveKaguneHandler,
    )
