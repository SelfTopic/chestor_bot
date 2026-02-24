import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.bot.repositories.user import UserRepository
from src.database.models import User

logger = logging.getLogger(__name__)


@dataclass
class BanResult:
    user: User
    banned_until: Optional[datetime]
    reason: Optional[str]


class BanService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def parse_duration(self, s: str) -> Optional[datetime]:
        """'7d', '24h', '30m' -> datetime. Всё остальное -> None (перманентно)."""
        units = {"m": "minutes", "h": "hours", "d": "days"}
        if len(s) >= 2 and s[-1] in units and s[:-1].isdigit():
            return datetime.now(timezone.utc) + timedelta(**{units[s[-1]]: int(s[:-1])})
        return None

    async def ban(
        self,
        query: str,
        duration_str: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> BanResult:
        user = await self._resolve_user(query)

        banned_until = None
        if duration_str:
            banned_until = self.parse_duration(duration_str)
            if banned_until is None:
                reason = f"{duration_str} {reason}".strip() if reason else duration_str

        await self.user_repo.ban(
            user.telegram_id, reason=reason, banned_until=banned_until
        )
        return BanResult(user=user, banned_until=banned_until, reason=reason)

    async def unban(self, query: str) -> User:
        user = await self._resolve_user(query)
        await self.user_repo.unban(user.telegram_id)
        return user

    async def _resolve_user(self, query: str) -> User:
        search = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
        user = await self.user_repo.get(search)

        if not user:
            raise ValueError(f"Пользователь не найден: {query}")

        return user

    def format_ban_result(self, result: BanResult) -> str:
        until_str = (
            f"до {result.banned_until.strftime('%d.%m.%Y %H:%M')} UTC"
            if result.banned_until
            else "навсегда"
        )
        return (
            f"🚫 Пользователь <code>{result.user.telegram_id}</code> "
            f"({result.user.full_name}) заблокирован {until_str}.\n"
            f"Причина: {result.reason or '—'}"
        )
