from aiogram import Dispatcher
from . import StartRouter

def include_routers(dp: Dispatcher) -> None:
    """Connects all routers on the dispatcher"""

    dp.include_routers(
        StartRouter,    
    )

__all__ = ["include_routers"]