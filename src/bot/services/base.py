from abc import ABC

from ..repositories import (
    ChatRepository,
    GhoulRepository,
    UserCooldownRepository,
    UserRepository,
)


class Base(ABC): 
    """Base service for managing data"""

    # Any service must have access to repositories

    user_repository: UserRepository
    ghoul_repository: GhoulRepository
    cooldown_repository: UserCooldownRepository
    chat_repository: ChatRepository

    def __init__(
        self,
        user_repository: UserRepository,
        ghoul_repository: GhoulRepository,
        user_cooldown_repository: UserCooldownRepository,
        chat_repository: ChatRepository

    ) -> None:
        self.user_repository = user_repository 
        self.ghoul_repository = ghoul_repository
        self.cooldown_repository = user_cooldown_repository
        self.chat_repository = chat_repository

    

__all__ = ["Base"]