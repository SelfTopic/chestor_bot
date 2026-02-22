from typing import Tuple

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..game_configs import STAT_UPGRADE_CONFIG, STATS
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

    def _cap(self, ghoul) -> int:
        return ghoul.level * 100

    def price_and_actual(self, cur_stat: int, want: int) -> Tuple[int, int]:
        price = STAT_UPGRADE_CONFIG.price(cur_stat, want)
        return price, want

    def build_message(self, ghoul, user) -> Tuple[str, InlineKeyboardMarkup]:
        lines = [f"Баланс: {user.balance if user else 0}", ""]
        cap = self._cap(ghoul)

        for label, key, emoji in STATS:
            cur = getattr(ghoul, key)
            remaining = max(0, cap - cur)
            prices = []
            for m in STAT_UPGRADE_CONFIG.multipliers:
                buy = min(m, remaining)
                if buy <= 0:
                    prices.append("—")
                else:
                    prices.append(str(STAT_UPGRADE_CONFIG.price(cur, buy)))

            lines.append(f"{emoji}{label}: {cur}  х5: {prices[1]} х10: {prices[2]}")

        lines.append("")

        inline_rows = []
        for label, key, emoji in STATS:
            cur: int = getattr(ghoul, key)
            remaining = max(0, cap - cur)
            buttons = []
            for m in STAT_UPGRADE_CONFIG.multipliers:
                buy = min(m, remaining)
                if buy <= 0:
                    buttons.append(
                        InlineKeyboardButton(
                            text=f"{emoji} +{m} (—)", callback_data="stat_nop"
                        )
                    )
                else:
                    price = STAT_UPGRADE_CONFIG.price(cur, buy)
                    buttons.append(
                        InlineKeyboardButton(
                            text=f"{emoji} +{m} ({price})",
                            callback_data=f"stat_buy_{key}_{m}",
                        )
                    )
            inline_rows.append(buttons)

        kb = InlineKeyboardMarkup(inline_keyboard=inline_rows)
        return "\n".join(lines), kb

    async def purchase(self, telegram_id: int, stat_key: str, count: int):
        ghoul = await self.ghoul_service.get(telegram_id)
        if not ghoul:
            raise ValueError("Ghoul not found")

        cur = getattr(ghoul, stat_key, None)
        if cur is None:
            raise ValueError("Unknown stat")

        cap = self._cap(ghoul)
        remaining = max(0, cap - cur)
        to_buy = min(count, remaining)
        if to_buy <= 0:
            return ghoul, None, 0, 0

        price = STAT_UPGRADE_CONFIG.price(cur, to_buy)

        user = await self.user_service.get(find_by=telegram_id)
        if not user:
            raise ValueError("User not found")

        if user.balance < price:
            return ghoul, user, 0, price

        await self.user_service.minus_balance(
            telegram_id=telegram_id, change_balance=price
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
