from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, PositiveInt, TypeAdapter

from src.database.models import PromoCode

from ..exceptions.promo import (
    PromoAlreadyActivated,
    PromoExhausted,
    PromoExpired,
    PromoNameTaken,
    PromoNotFound,
)
from ..game_configs import StatKey, stat_cap_for_level
from ..repositories.ghoul import GhoulRepository
from ..repositories.promo import PromoRepository
from ..utils import utcnow_naive
from .level_up import LevelUpService
from .user import UserService


class ChestonReward(BaseModel, frozen=True):
    kind: Literal["cheston"] = "cheston"
    amount: PositiveInt


class RcReward(BaseModel, frozen=True):
    kind: Literal["rc"] = "rc"
    amount: PositiveInt


class LevelProgressReward(BaseModel, frozen=True):
    kind: Literal["progress"] = "progress"
    percent: PositiveInt


class StatReward(BaseModel, frozen=True):
    kind: Literal["stat"] = "stat"
    stat: StatKey
    amount: PositiveInt


Reward = Annotated[
    ChestonReward | RcReward | LevelProgressReward | StatReward, Field(discriminator="kind")
]


@dataclass(frozen=True)
class Granted:
    reward: Reward
    capped_to: Optional[int] = None

_REWARDS = TypeAdapter(list[Reward])


class PromoService:
    def __init__(
        self,
        promo_repository: PromoRepository,
        ghoul_repository: GhoulRepository,
        user_service: UserService,
        level_up_service: LevelUpService,
    ) -> None:
        self.promo_repository = promo_repository
        self.ghoul_repository = ghoul_repository
        self.user_service = user_service
        self.level_up_service = level_up_service

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

    async def activate(self, name: str, telegram_id: int) -> list[Granted]:
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

        return [
            await self._grant(reward, telegram_id, promo.name) for reward in self.rewards(promo)
        ]

    async def _grant(self, reward: Reward, telegram_id: int, promo_name: str) -> Granted:
        match reward:
            case ChestonReward(amount=amount):
                await self.user_service.plus_balance(
                    telegram_id, amount, log=f"promo {promo_name}"
                )
            case RcReward(amount=amount):
                await self.ghoul_repository.increment_fields(
                    telegram_id, rc_money=amount, lifetime_rc_earned=amount
                )
            case LevelProgressReward(percent=percent):
                await self.level_up_service.add_progress(telegram_id, percent)
            case StatReward(stat=stat, amount=amount):
                return await self._grant_stat(reward, telegram_id, stat, amount)
        return Granted(reward)

    # Потолок стата по уровню, как у покупки: ошибка в промокоде не сломает баланс боёв.
    async def _grant_stat(
        self, reward: StatReward, telegram_id: int, stat: StatKey, amount: int
    ) -> Granted:
        ghoul = await self.ghoul_repository.get(telegram_id)
        if ghoul is None:
            return Granted(reward, capped_to=0)
        room = max(0, stat_cap_for_level(ghoul.level, stat) - getattr(ghoul, stat))
        added = min(amount, room)
        if added:
            deltas = {stat: added}
            if stat == "max_health":
                deltas["health"] = added
            await self.ghoul_repository.increment_fields(telegram_id, **deltas)
        return Granted(reward) if added == amount else Granted(reward, capped_to=added)
