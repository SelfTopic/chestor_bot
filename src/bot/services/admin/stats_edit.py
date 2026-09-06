import logging
from dataclasses import dataclass

from src.bot.repositories.balances_log import BalancesLogRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.database.models import Ghoul, User

logger = logging.getLogger(__name__)

ALLOWED_USER_FIELDS = {"balance", "is_banned", "ban_reason", "banned_until"}
ALLOWED_GHOUL_FIELDS = {
    "rc_money",
    "level",
    "strength",
    "dexterity",
    "speed",
    "health",
    "max_health",
    "regeneration",
    "hunger",
    "kagune_strength",
    "snap_count",
    "eat_humans",
    "eat_ghouls",
    "coffee_count",
}


@dataclass
class StatEditResult:
    target: User | Ghoul
    field: str
    value: int
    is_ghoul_field: bool


class StatsEditService:
    def __init__(
        self,
        user_repo: UserRepository,
        ghoul_repo: GhoulRepository,
        balances_log_repo: BalancesLogRepository,
    ):
        self.user_repo = user_repo
        self.ghoul_repo = ghoul_repo
        self.balances_log_repo = balances_log_repo

    def resolve_field(self, field: str) -> tuple[bool, bool]:
        """Возвращает (is_valid, is_ghoul_field)."""
        if field in ALLOWED_USER_FIELDS:
            return True, False
        if field in ALLOWED_GHOUL_FIELDS:
            return True, True
        return False, False

    async def set_stat(
        self, query: str, field: str, value: int, admin_id: int
    ) -> StatEditResult:
        search = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
        user = await self.user_repo.get(search)

        if not user:
            raise ValueError(f"Пользователь не найден: {query}")

        is_valid, is_ghoul_field = self.resolve_field(field)
        if not is_valid:
            raise ValueError(f"Неизвестное поле: {field}")

        if not is_ghoul_field:
            if field == "balance":
                before_balance = user.balance
                updated = await self.user_repo.change_data(
                    user.telegram_id, balance=value
                )
                await self.balances_log_repo.insert(
                    telegram_id=user.telegram_id,
                    change_balance=value - before_balance,
                    before_balance=before_balance,
                    after_balance=value,
                    log=f"admin override by {admin_id}",
                )
            else:
                updated = await self.user_repo.change_data(
                    user.telegram_id, **{field: value}
                )
            return StatEditResult(
                target=updated, field=field, value=value, is_ghoul_field=False
            )

        ghoul = await self.ghoul_repo.get(user.telegram_id)
        if not ghoul:
            raise ValueError("У пользователя нет профиля гуля.")

        updated_ghoul = await self.ghoul_repo.upsert(user.telegram_id, **{field: value})
        return StatEditResult(
            target=updated_ghoul, field=field, value=value, is_ghoul_field=True
        )

    def format_fields_help(self) -> str:
        return (
            f"Поля пользователя: {', '.join(sorted(ALLOWED_USER_FIELDS))}\n"
            f"Поля гуля: {', '.join(sorted(ALLOWED_GHOUL_FIELDS))}"
        )
