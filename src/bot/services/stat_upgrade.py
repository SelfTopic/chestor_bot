from typing import Tuple

from ..game_configs import STAT_UPGRADE_CONFIG, stat_cap_for_level
from ..services import DialogService, GhoulService, UserService


class StatUpgradeService:
    def __init__(
        self,
        ghoul_service: GhoulService,
        user_service: UserService,
        dialog_service: DialogService,
    ):
        self.ghoul_service = ghoul_service
        self.user_service = user_service
        self.dialog_service = dialog_service

    def _cap(self, ghoul, stat_key: str) -> int:
        return stat_cap_for_level(ghoul.level, stat_key)

    def price_and_actual(self, cur_stat: int, want: int, stat_key: str = "") -> Tuple[int, int]:
        price = STAT_UPGRADE_CONFIG.price(cur_stat, want, stat_key)
        return price, want

    async def purchase(self, telegram_id: int, stat_key: str, count: int):
        ghoul = await self.ghoul_service.get(telegram_id)
        if not ghoul:
            raise ValueError("Ghoul not found")

        cur = getattr(ghoul, stat_key, None)
        if cur is None:
            raise ValueError("Unknown stat")

        cap = self._cap(ghoul, stat_key)
        remaining = max(0, cap - cur)
        to_buy = min(count, remaining)
        if to_buy <= 0:
            return ghoul, None, 0, 0

        price = STAT_UPGRADE_CONFIG.price(cur, to_buy, stat_key)

        user = await self.user_service.get(find_by=telegram_id)
        if not user:
            raise ValueError("User not found")

        if user.balance < price:
            return ghoul, user, 0, price

        await self.user_service.minus_balance(
            telegram_id=telegram_id, change_balance=price, log="stat upgrade"
        )

        new_value = cur + to_buy
        update_kwargs = {stat_key: new_value}
        if stat_key == "max_health":
            update_kwargs.update({"health": ghoul.health + to_buy})

        new_ghoul = await self.ghoul_service.upsert(
            telegram_id=telegram_id, **update_kwargs
        )
        new_user = await self.user_service.get(find_by=telegram_id)

        return new_ghoul, new_user, to_buy, price


__all__ = ["StatUpgradeService"]
