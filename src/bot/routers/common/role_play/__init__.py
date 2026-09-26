from selfrot import BaseRouter

from ....context import AppContext
from .manage import (
    DeleteRpHandler,
    GetAllRpHandler,
    NewRpHandler,
    NewRpOnMediaHandler,
)
from .middleware import RpCommandsMiddleware
from .play import RolePlayHandler


class RolePlayRouter(BaseRouter[AppContext]):
    middlewares = (RpCommandsMiddleware,)
    # порядок как у прода: сначала управление командами, потом сами команды
    handlers = (
        NewRpOnMediaHandler,
        NewRpHandler,
        GetAllRpHandler,
        DeleteRpHandler,
        RolePlayHandler,
    )
