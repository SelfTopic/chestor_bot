import logging
from dataclasses import dataclass
from typing import Optional

from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.database.models import Ghoul, User

logger = logging.getLogger(__name__)


@dataclass
class PlayerProfile:
    user: User
    ghoul: Optional[Ghoul]


class PlayerLookupService:
    def __init__(self, user_repo: UserRepository, ghoul_repo: GhoulRepository):
        self.user_repo = user_repo
        self.ghoul_repo = ghoul_repo

    async def get_profile(self, query: str) -> Optional[PlayerProfile]:
        search = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
        user = await self.user_repo.get(search)

        if not user:
            return None

        ghoul = await self.ghoul_repo.get(user.telegram_id)
        return PlayerProfile(user=user, ghoul=ghoul)
