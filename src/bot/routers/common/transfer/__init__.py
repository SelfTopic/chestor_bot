from selfrot import BaseRouter

from ....context import AppContext
from .confirmation import TransferStep1Handler, TransferStep2Handler
from .handlers import TransferToRepliedHandler, TransferToUserHandler


class TransferRouter(BaseRouter[AppContext]):
    # Порядок важен: апдейт достаётся первому подошедшему хендлеру.
    handlers = (
        TransferToRepliedHandler,
        TransferToUserHandler,
        TransferStep1Handler,
        TransferStep2Handler,
    )
