from dataclasses import dataclass
from datetime import datetime, timedelta

from src.bot.game_configs import CULT_CONFIG
from src.bot.repositories import UserRepository
from src.bot.services.user import UserService


@dataclass(frozen=True)
class CultPayout:
    telegram_id: int
    notify: bool


class CultService:
    def __init__(self, user_repository: UserRepository, user_service: UserService) -> None:
        self.user_repository = user_repository
        self.user_service = user_service

    async def pay_due(self, now: datetime) -> list[CultPayout]:
        claimed = await self.user_repository.claim_cult_rewards(
            CULT_CONFIG.hashtags,
            active_since=now - timedelta(seconds=CULT_CONFIG.active_within_seconds),
            due_before=now - timedelta(seconds=CULT_CONFIG.interval_seconds),
            now=now,
        )
        for telegram_id, _ in claimed:
            await self.user_service.plus_balance(
                telegram_id, CULT_CONFIG.reward, log="cult hashtag reward"
            )
        return [CultPayout(telegram_id, notify) for telegram_id, notify in claimed]

    async def mute(self, telegram_id: int) -> None:
        await self.user_repository.change_data(telegram_id, cult_notifications=False)


__all__ = ["CultPayout", "CultService"]
