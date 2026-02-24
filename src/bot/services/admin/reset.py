import logging
from dataclasses import dataclass

from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository

logger = logging.getLogger(__name__)


@dataclass
class ResetResult:
    telegram_id: int
    user_deleted: bool
    ghoul_deleted: bool


class ResetService:
    def __init__(self, user_repo: UserRepository, ghoul_repo: GhoulRepository):
        self.user_repo = user_repo
        self.ghoul_repo = ghoul_repo

    async def reset_ghoul(self, query: str) -> ResetResult:
        """Удаляет только профиль гуля."""
        user = await self._resolve_user(query)
        ghoul_deleted = await self.ghoul_repo.delete(user.telegram_id)
        return ResetResult(
            telegram_id=user.telegram_id,
            user_deleted=False,
            ghoul_deleted=ghoul_deleted,
        )

    async def reset_user(self, query: str) -> ResetResult:
        """Удаляет пользователя полностью (каскадно удалит гуля если есть FK)."""
        user = await self._resolve_user(query)

        # Сначала гуль — на случай если нет CASCADE в БД
        ghoul_deleted = await self.ghoul_repo.delete(user.telegram_id)
        user_deleted = await self.user_repo.delete(user.telegram_id)

        return ResetResult(
            telegram_id=user.telegram_id,
            user_deleted=user_deleted,
            ghoul_deleted=ghoul_deleted,
        )

    async def _resolve_user(self, query: str):
        search = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
        user = await self.user_repo.get(search)
        if not user:
            raise ValueError(f"Пользователь не найден: {query}")
        return user
