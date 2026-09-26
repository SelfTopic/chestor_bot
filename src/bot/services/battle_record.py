import logging
from datetime import timedelta
from typing import Optional

from ..repositories import ActiveBattleRepository, BattleRepository
from ..utils import utcnow_naive

logger = logging.getLogger(__name__)

_DAY = timedelta(hours=24)


class BattleRecordService:
    def __init__(
        self,
        active_battle_repository: ActiveBattleRepository,
        battle_repository: BattleRepository,
    ) -> None:
        self.active_battle_repository = active_battle_repository
        self.battle_repository = battle_repository


    async def try_claim_mob_fight(self, telegram_id: int) -> bool:
        return await self.active_battle_repository.try_claim(
            [
                {
                    "telegram_id": telegram_id,
                    "opponent_telegram_id": None,
                    "battle_type": "mob",
                    "status": "active",
                }
            ]
        )

    async def try_claim_duel(
        self, telegram_id_a: int, telegram_id_b: int, status: str = "pending_confirmation"
    ) -> bool:
        return await self.active_battle_repository.try_claim(
            [
                {
                    "telegram_id": telegram_id_a,
                    "opponent_telegram_id": telegram_id_b,
                    "battle_type": "duel",
                    "status": status,
                },
                {
                    "telegram_id": telegram_id_b,
                    "opponent_telegram_id": telegram_id_a,
                    "battle_type": "duel",
                    "status": status,
                },
            ]
        )

    async def release(self, *telegram_ids: int) -> None:
        await self.active_battle_repository.release(list(telegram_ids))

    async def is_busy(self, telegram_id: int) -> bool:
        return await self.active_battle_repository.get(telegram_id) is not None


    async def record_mob_fight(
        self,
        telegram_id: int,
        mob_name: str,
        winner: Optional[str],
        ended_naturally: bool,
        is_forced: bool = False,
        reward_level_progress: Optional[float] = None,
        reward_rc: Optional[int] = None,
        reward_balance: Optional[int] = None,
    ) -> None:
        await self.battle_repository.insert(
            battle_type="mob",
            participant_a_telegram_id=telegram_id,
            participant_b_telegram_id=None,
            mob_name=mob_name,
            winner=winner,
            ended_naturally=ended_naturally,
            is_forced=is_forced,
            reward_level_progress=reward_level_progress,
            reward_rc=reward_rc,
            reward_balance=reward_balance,
        )

    async def record_duel(
        self,
        telegram_id_a: int,
        telegram_id_b: int,
        winner: Optional[str],
        ended_naturally: bool,
        is_forced: bool = False,
        winner_choice: Optional[str] = None,
        reward_level_progress: Optional[float] = None,
        reward_rc: Optional[int] = None,
        reward_balance: Optional[int] = None,
    ) -> None:
        await self.battle_repository.insert(
            battle_type="duel",
            participant_a_telegram_id=telegram_id_a,
            participant_b_telegram_id=telegram_id_b,
            mob_name=None,
            winner=winner,
            ended_naturally=ended_naturally,
            is_forced=is_forced,
            winner_choice=winner_choice,
            reward_level_progress=reward_level_progress,
            reward_rc=reward_rc,
            reward_balance=reward_balance,
        )

    async def count_total_last_24h(self, telegram_id: int) -> int:
        return await self.battle_repository.count_total_since(telegram_id, utcnow_naive() - _DAY)

    async def count_pair_last_24h(self, telegram_id_a: int, telegram_id_b: int) -> int:
        return await self.battle_repository.count_pair_since(
            telegram_id_a, telegram_id_b, utcnow_naive() - _DAY
        )


    async def count_wins(self, telegram_id: int) -> int:
        return await self.battle_repository.count_wins(telegram_id)

    async def count_wins_vs_players(self, telegram_id: int) -> int:
        return await self.battle_repository.count_wins(telegram_id, battle_type="duel")

    async def count_wins_vs_mobs(self, telegram_id: int) -> int:
        return await self.battle_repository.count_wins(telegram_id, battle_type="mob")

    async def count_losses(self, telegram_id: int) -> int:
        return await self.battle_repository.count_losses(telegram_id)

    async def count_losses_vs_players(self, telegram_id: int) -> int:
        return await self.battle_repository.count_losses(telegram_id, battle_type="duel")

    async def count_losses_vs_mobs(self, telegram_id: int) -> int:
        return await self.battle_repository.count_losses(telegram_id, battle_type="mob")

    async def count_total_battles(self, telegram_id: int) -> int:
        return await self.battle_repository.count_total(telegram_id)

    async def count_total_battles_vs_players(self, telegram_id: int) -> int:
        return await self.battle_repository.count_total(telegram_id, battle_type="duel")

    async def count_total_battles_vs_mobs(self, telegram_id: int) -> int:
        return await self.battle_repository.count_total(telegram_id, battle_type="mob")


__all__ = ["BattleRecordService"]
