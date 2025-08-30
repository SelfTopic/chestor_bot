from abc import ABC 

from ..repositories import (
    UserRepository,
    GhoulRepository,
    UserCooldownRepository
)
class Base(ABC): 
    """Base service for managing data"""

    # Any service must have access to repositories

    user_repository: UserRepository
    ghoul_repository: GhoulRepository
    cooldown_repository: UserCooldownRepository

    def __init__(
        self,
        user_repository: UserRepository,
        ghoul_repository: GhoulRepository,
        user_cooldown_repository: UserCooldownRepository
    ) -> None:
        self.user_repository = user_repository 
        self.ghoul_repository = ghoul_repository
        self.cooldown_repository = user_cooldown_repository

    

__all__ = ["Base"]