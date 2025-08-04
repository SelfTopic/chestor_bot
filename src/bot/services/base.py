from abc import ABC 

from ..repositories import UserRepository

class Base(ABC): 
    """Base service for managing data"""

    # Any service must have access to repositories

    userRepository: UserRepository

    def __init__(
        self,
        userRepository: UserRepository
    ) -> None:
        self.userRepository = userRepository 

    

__all__ = ["Base"]