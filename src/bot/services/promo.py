from datetime import timedelta
from typing import Literal, Optional

from pydantic import BaseModel, PositiveInt, TypeAdapter

from src.database.models import PromoCode

from ..exceptions.promo import (
    PromoAlreadyActivated,
    PromoExhausted,
    PromoExpired,
    PromoNameTaken,
    PromoNotFound,
)
from ..repositories.promo import PromoRepository
from ..utils import utcnow_naive
from .user import UserService


class ChestonReward(BaseModel, frozen=True):
    kind: Literal["cheston"] = "cheston"
    amount: PositiveInt


Reward = ChestonReward

_REWARDS = TypeAdapter(list[Reward])


class PromoService:
    def __init__(self, promo_repository: PromoRepository, user_service: UserService) -> None:
        self.promo_repository = promo_repository
        self.user_service = user_service

    async def create(
        self,
        name: str,
        rewards: list[Reward],
        activations: int,
        lifetime: Optional[timedelta],
        created_by: int,
    ) -> PromoCode:
        promo = await self.promo_repository.create(
            name=name.casefold(),
            rewards=_REWARDS.dump_python(rewards, mode="json"),
            activations_limit=activations,
            expires_at=utcnow_naive() + lifetime if lifetime else None,
            created_by=created_by,
        )
        if promo is None:
            raise PromoNameTaken(name)
        return promo

    def rewards(self, promo: PromoCode) -> list[Reward]:
        return _REWARDS.validate_python(promo.rewards)

    async def activate(self, name: str, telegram_id: int) -> list[Reward]:
        repository = self.promo_repository
        promo = await repository.by_name(name.casefold())
        if promo is None:
            raise PromoNotFound(name)
        if promo.expires_at is not None and promo.expires_at <= utcnow_naive():
            raise PromoExpired(name)
        if not await repository.record_activation(promo.id, telegram_id):
            raise PromoAlreadyActivated(name)
        if not await repository.claim_activation(promo.id):
            raise PromoExhausted(name)

        rewards = self.rewards(promo)
        for reward in rewards:
            await self._grant(reward, telegram_id, promo.name)
        return rewards

    async def _grant(self, reward: Reward, telegram_id: int, promo_name: str) -> None:
        match reward:
            case ChestonReward(amount=amount):
                await self.user_service.plus_balance(
                    telegram_id, amount, log=f"promo {promo_name}"
                )
