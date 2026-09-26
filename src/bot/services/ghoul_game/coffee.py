import logging

from ...game_configs import COFFEE_CONFIG
from ...services.cooldown import CooldownService
from ...services.ghoul import GhoulService
from ...services.user import UserService
from ...types.coffee import CoffeeResult

logger = logging.getLogger(__name__)


class CoffeeService:
    def __init__(
        self,
        ghoul_service: GhoulService,
        cooldown_service: CooldownService,
        user_service: UserService,
    ):
        self.ghoul_service = ghoul_service
        self.cooldown_service = cooldown_service
        self.user_service = user_service

    async def execute(self, user_id: int):
        money = COFFEE_CONFIG.award

        ghoul = await self.ghoul_service.coffee(telegram_id=user_id)
        user = await self.user_service.plus_balance(
            telegram_id=user_id, change_balance=money, log="coffee award"
        )

        return CoffeeResult(ghoul=ghoul, user=user, award=money)

    async def execute_cooldown(self, user_id: int, cooldown_name: str = "COFFEE"):
        cooldown = await self.cooldown_service.get_active_cooldown(
            telegram_id=user_id, cooldown_name=cooldown_name
        )

        cooldown_day = await self.cooldown_service.get_active_cooldown(
            telegram_id=user_id, cooldown_name="COFFEE_DAY"
        )

        if cooldown_day:
            return cooldown_day

        if cooldown:
            if cooldown_day:
                return cooldown_day

            result_cooldown = await self.cooldown_service.set_cooldown(
                telegram_id=user_id, cooldown_type="COFFEE_DAY"
            )
            await self.user_service.minus_balance(
                telegram_id=user_id,
                change_balance=COFFEE_CONFIG.award,
                log="coffee refund on cooldown",
            )
            return result_cooldown

        await self.cooldown_service.set_cooldown(
            telegram_id=user_id, cooldown_type=cooldown_name
        )

        return None
