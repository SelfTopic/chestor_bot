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
    handlers = (
        NewRpOnMediaHandler,
        NewRpHandler,
        GetAllRpHandler,
        DeleteRpHandler,
        RolePlayHandler,
    )
