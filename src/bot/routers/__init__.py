from .start_router import router as StartRouter 
from .bot_router import router as BotRouter
from .error_router import router as ErrorRouter

__all__ = [
    "StartRouter",
    "BotRouter",
    "ErrorRouter"
]