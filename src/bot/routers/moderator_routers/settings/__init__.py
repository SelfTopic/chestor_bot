from selfrot import BaseRouter

from ....context import AppContext
from .defaults import BanDefaultHandler, MuteDefaultHandler
from .voice import VoiceHandler


class SettingsRouter(BaseRouter[AppContext]):
    handlers = (MuteDefaultHandler, BanDefaultHandler, VoiceHandler)
