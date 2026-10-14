from selfrot import BaseRouter

from ....context import AppContext
from .admin_chat import AdminChatHandler
from .defaults import BanDefaultHandler, MuteDefaultHandler
from .menu import (
    ModerationMenuHandler,
    ModerationMenuLabelHandler,
    ModerationMenuPressHandler,
)
from .voice import VoiceHandler
from .warns import WarnExpiryHandler, WarnLimitHandler, WarnPenaltyHandler


class SettingsRouter(BaseRouter[AppContext]):
    handlers = (
        ModerationMenuHandler,
        ModerationMenuLabelHandler,
        ModerationMenuPressHandler,
        MuteDefaultHandler,
        BanDefaultHandler,
        VoiceHandler,
        AdminChatHandler,
        WarnLimitHandler,
        WarnPenaltyHandler,
        WarnExpiryHandler,
    )
