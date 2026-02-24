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

    def format_profile(self, profile: PlayerProfile) -> str:
        user = profile.user
        ghoul = profile.ghoul

        ban_status = "🚫 Забанен" if user.is_banned else "✅ Активен"
        ban_info = ""
        if user.is_banned:
            until = (
                f"до {user.banned_until.strftime('%d.%m.%Y %H:%M')} UTC"
                if user.banned_until
                else "навсегда"
            )
            ban_info = f"\nПричина: {user.ban_reason or '—'}\nСрок: {until}"

        ghoul_info = ""
        if ghoul:
            ghoul_info = (
                f"\n\n<b>Гуль:</b>"
                f"\nУровень: {ghoul.level}"
                f"\nRC-деньги: {ghoul.rc_money}"
                f"\nСила: {ghoul.strength} | Ловкость: {ghoul.dexterity} | Скорость: {ghoul.speed}"
                f"\nЗдоровье: {ghoul.health}/{ghoul.max_health}"
                f"\nРегенерация: {ghoul.regeneration}"
                f"\nГолод: {ghoul.hunger}"
                f"\nKakuja: {'да' if ghoul.is_kakuja else 'нет'}"
            )

        return (
            f"<b>Профиль игрока</b>\n"
            f"ID: <code>{user.telegram_id}</code>\n"
            f"Имя: {user.full_name}\n"
            f"Username: @{user.username or '—'}\n"
            f"Баланс: {user.balance}\n"
            f"Статус: {ban_status}{ban_info}"
            f"{ghoul_info}"
        )
