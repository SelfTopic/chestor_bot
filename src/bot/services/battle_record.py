"""Персистентность вокруг боя - ДВЕ разные вещи в одном сервисе, у них
общий жизненный цикл (claim -> бой играется -> release + record, всегда
вместе, всегда в этом порядке), поэтому не разнесены на 2 крошечных
сервиса:

1) "Занятость прямо сейчас" (`ActiveBattle`) - эфемерный лок, не даёт
   гулю оказаться в двух боях одновременно. Найдено как реальный эксплойт
   (см. чат): пригласить себя с твинка на дуэль и ОДНОВРЕМЕННО затеять бой
   с мобом - без лока оба боя резолвятся независимо, и в зависимости от
   того, чья запись урона в БД "победит" последней, можно фактически
   фармить мобов без потери HP. Защита - на уровне БД (PK-конфликт в
   `active_battles`, см. `ActiveBattleRepository.try_claim`), а не
   "проверить-потом-создать" в коде - именно "проверить, а не занято ли"
   отдельным шагом ДО создания брони и есть тот самый race condition,
   который эксплойт использует.

2) "История боёв" (`Battle`) - постоянный лог для будущих дневных лимитов
   (5/пара, 20/всего - BATTLE_ENGINE.md 4.4) и счётчика побед/поражений в
   профиле (5.2)."""

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

    # --- Занятость (лок) ----------------------------------------------------

    async def try_claim_mob_fight(self, telegram_id: int) -> bool:
        """True - занято, можно начинать бой. False - этот гуль уже в
        каком-то бою (pending или active) - начинать нельзя."""

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
        """Занимает ОБЕИХ участников одной атомарной операцией - либо оба
        успешно заняты, либо НИ ОДИН (см. ActiveBattleRepository.try_claim) -
        именно это закрывает эксплойт "одновременно два боя"."""

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
        """Вызывать, когда бой разрешился (или отклонён/просрочен) -
        освобождает участников для следующего боя."""

        await self.active_battle_repository.release(list(telegram_ids))

    async def is_busy(self, telegram_id: int) -> bool:
        """Готовый источник для `BattleService.validate_ghoul(...,
        has_pending_confirmation=...)`, когда появится реальный роутер
        дуэлей/боя с мобом - сейчас им никто не пользуется (mob_fight_preview
        не персистентна и не должна занимать лок)."""

        return await self.active_battle_repository.get(telegram_id) is not None

    # --- История --------------------------------------------------------------

    async def record_mob_fight(
        self,
        telegram_id: int,
        mob_name: str,
        winner: Optional[str],
        ended_naturally: bool,
        is_forced: bool = False,
        reward_level_progress: Optional[float] = None,
        reward_rc: Optional[int] = None,
    ) -> None:
        """`winner_choice`/`reward_balance` не принимаются - "ограбить/
        отпустить/съесть" (см. BATTLE_DESIGN.md "Исход боя") применимо
        только к дуэли, у моба нет ни баланса, ни строки `User`."""

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
        """Счётчик побед за всё время - для профиля (BATTLE_ENGINE.md 5.2),
        не для дневных лимитов (см. count_total_last_24h)."""

        return await self.battle_repository.count_wins(telegram_id)

    async def count_losses(self, telegram_id: int) -> int:
        return await self.battle_repository.count_losses(telegram_id)

    async def count_total_battles(self, telegram_id: int) -> int:
        return await self.battle_repository.count_total(telegram_id)


__all__ = ["BattleRecordService"]
