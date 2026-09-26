from selfrot import BaseRouter

from ....context import AppContext
from .confirmation import TransferStep1Handler, TransferStep2Handler
from .handlers import TransferToRepliedHandler, TransferToUserHandler


class TransferRouter(BaseRouter[AppContext]):
    # Порядок важен: апдейт достаётся первому подошедшему. Команда с ответом и без
    # ответа взаимоисключают друг друга, шаги различаются состоянием диалога.
    handlers = (
        TransferToRepliedHandler,
        TransferToUserHandler,
        TransferStep1Handler,
        TransferStep2Handler,
    )
