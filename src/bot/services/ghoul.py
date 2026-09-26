import logging
import random
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

from src.database.models import Ghoul

from ..game_configs import EAT_HUMAN_CONFIG, KAGUNE_CONFIG
from ..repositories import DeathLogRepository, ScheduledNotificationRepository
from ..types import KaguneType, NotificationType, Race, RegisterGhoulType
from ..utils import (
    apply_hunger_restore,
    compute_health,
    compute_hunger,
    health_regen_per_hour,
    hours_until_full_health,
    hours_until_hunger_threshold,
    next_hunger_threshold,
    utcnow_naive,
)
from .base import Base

logger = logging.getLogger(__name__)


class GhoulService(Base):
    def __init__(
        self,
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
        notification_repository: Optional[ScheduledNotificationRepository] = None,
        death_log_repository: Optional[DeathLogRepository] = None,
    ) -> None:
        super().__init__(
            user_repository, ghoul_repository, user_cooldown_repository, chat_repository
        )
        self.notification_repository = notification_repository
        self.death_log_repository = death_log_repository

    async def get(self, find_by: int) -> Optional[Ghoul]:
        logger.debug(f"Called method get. Params: find_by={find_by}")

        if find_by > 666000:
            logger.debug(f"Looking up by Telegram ID: {find_by}")
            ghoul = await self.ghoul_repository.get(find_by)
        else:
            logger.debug(f"Looking up by custom ID: {find_by}")
            ghoul = await self.ghoul_repository.get_by_id(find_by)

        logger.debug(f"Ghoul found: {ghoul is not None}")
        if ghoul:
            ghoul = await self.materialize_passive_stats(ghoul)
        return ghoul

    async def materialize_passive_stats(self, ghoul: Ghoul) -> Ghoul:
        if ghoul.is_dead:
            return ghoul

        now = utcnow_naive()

        new_hunger, new_hunger_at, would_starve = compute_hunger(
            hunger=ghoul.hunger,
            hunger_updated_at=ghoul.hunger_updated_at,
            is_kakuja=ghoul.is_kakuja,
            now=now,
        )

        if would_starve:
            return await self.apply_death(ghoul.telegram_id, cause="starvation")

        hp_per_hour = health_regen_per_hour(
            regeneration=ghoul.regeneration,
            hunger=new_hunger,
            kagune_type_bit=ghoul.kagune_type_bit or 0,
            is_kakuja=ghoul.is_kakuja,
        )
        new_health, new_health_at = compute_health(
            health=ghoul.health,
            health_updated_at=ghoul.health_updated_at,
            max_health=ghoul.max_health,
            hp_per_hour=hp_per_hour,
            now=now,
        )

        if new_hunger == ghoul.hunger and new_health == ghoul.health:
            result = ghoul
        else:
            logger.debug(
                f"Materializing passive stats for ghoul {ghoul.telegram_id}: "
                f"hunger {ghoul.hunger}->{new_hunger}, health {ghoul.health}->{new_health}"
            )
            result = await self.ghoul_repository.upsert(
                telegram_id=ghoul.telegram_id,
                hunger=new_hunger,
                hunger_updated_at=new_hunger_at,
                health=new_health,
                health_updated_at=new_health_at,
            )

        # Расписание пересчитывается всегда, иначе правка через /set_stat не переставит уже
        # стоящий пуш.
        if self.notification_repository is not None:
            await self.sync_notification_schedule(result, now=now)

        return result

    _REBIRTH_SURVIVORS = {"id", "telegram_id", "created_at", "deaths", "updated_at"}
    _REBIRTH_TIMESTAMP_COLUMNS = {"health_updated_at", "hunger_updated_at"}

    def _rebirth_reset_values(self) -> dict:
        values: dict = {}
        for column in Ghoul.__table__.columns:
            name = column.name
            if name in self._REBIRTH_SURVIVORS or name in self._REBIRTH_TIMESTAMP_COLUMNS:
                continue
            if column.default is not None and column.default.is_scalar:
                values[name] = column.default.arg
            elif column.nullable:
                values[name] = None
        return values

    async def apply_death(
        self,
        telegram_id: int,
        cause: str,
        killer_telegram_id: Optional[int] = None,
    ) -> Ghoul:
        # Не self.get(): он снова вызовет materialize_passive_stats, а та — apply_death, и
        # так по кругу.
        ghoul = await self.ghoul_repository.get(telegram_id)
        if not ghoul:
            raise ValueError("Ghoul not found")

        if self.death_log_repository is not None:
            await self.death_log_repository.insert(
                telegram_id=telegram_id,
                cause=cause,
                level=ghoul.level,
                lifetime_rc_earned=ghoul.lifetime_rc_earned,
                killer_telegram_id=killer_telegram_id,
            )

        await self.increment_fields(telegram_id, deaths=1)
        updated = await self.set_fields(telegram_id, is_dead=True)

        if self.notification_repository is not None:
            await self.notification_repository.delete(
                telegram_id, NotificationType.HEALTH_FULL
            )
            await self.notification_repository.delete(
                telegram_id, NotificationType.HUNGER_THRESHOLD
            )
            await self.notification_repository.schedule(
                telegram_id=telegram_id,
                notification_type=NotificationType.DEATH,
                fire_at=utcnow_naive(),
            )

        return updated

    async def reset_for_rebirth(self, telegram_id: int) -> Ghoul:
        ghoul = await self.get(telegram_id)
        if not ghoul:
            raise ValueError("Ghoul not found")

        values = self._rebirth_reset_values()
        now = utcnow_naive()
        values["health_updated_at"] = now
        values["hunger_updated_at"] = now

        new_kagune = self._first_kagune()
        values["kagune_type_bit"] = new_kagune.value["bit"]
        values[new_kagune.value["strength_column"]] = 1

        return await self.set_fields(telegram_id, **values)

    async def sync_notification_schedule(self, ghoul: Ghoul, now: datetime) -> None:
        if self.notification_repository is None:
            return

        hp_per_hour = health_regen_per_hour(
            regeneration=ghoul.regeneration,
            hunger=ghoul.hunger,
            kagune_type_bit=ghoul.kagune_type_bit or 0,
            is_kakuja=ghoul.is_kakuja,
        )
        hours_to_full = hours_until_full_health(ghoul.health, ghoul.max_health, hp_per_hour)

        if not hours_to_full:
            await self.notification_repository.delete(
                ghoul.telegram_id, NotificationType.HEALTH_FULL
            )
        else:
            await self.notification_repository.schedule(
                telegram_id=ghoul.telegram_id,
                notification_type=NotificationType.HEALTH_FULL,
                fire_at=now + timedelta(hours=hours_to_full),
            )

        threshold = next_hunger_threshold(ghoul.hunger)
        hours_to_threshold = hours_until_hunger_threshold(
            ghoul.hunger, ghoul.is_kakuja, threshold
        )
        await self.notification_repository.schedule(
            telegram_id=ghoul.telegram_id,
            notification_type=NotificationType.HUNGER_THRESHOLD,
            fire_at=now + timedelta(hours=hours_to_threshold),
            threshold=threshold,
        )

    async def increment_fields(self, telegram_id: int, **deltas: int) -> Optional[Ghoul]:
        return await self.ghoul_repository.increment_fields(telegram_id, **deltas)

    async def set_fields(self, telegram_id: int, **values: Any) -> Ghoul:
        return await self.ghoul_repository.upsert(telegram_id, **values)

    async def restore_hunger_from_eating(
        self, telegram_id: int, **extra_upsert_fields: Any
    ) -> Tuple[Ghoul, int]:
        logger.debug(
            f"Called method restore_hunger_from_eating. Params: telegram_id={telegram_id}"
        )

        ghoul = await self.get(telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for restore_hunger_from_eating operation")
            raise ValueError("Ghoul not found")

        restore = EAT_HUMAN_CONFIG.hunger_restore
        new_hunger = apply_hunger_restore(ghoul.hunger, restore)

        updated_ghoul = await self.ghoul_repository.upsert(
            telegram_id=telegram_id,
            hunger=new_hunger,
            hunger_updated_at=utcnow_naive(),
            **extra_upsert_fields,
        )

        await self.sync_notification_schedule(updated_ghoul, now=utcnow_naive())

        logger.debug(
            f"restore_hunger_from_eating: hunger {ghoul.hunger}->{new_hunger} (+{restore})"
        )

        return updated_ghoul, restore

    async def eat_human(self, telegram_id: int) -> Tuple[Ghoul, int]:
        logger.debug(f"Called method eat_human. Params: telegram_id={telegram_id}")

        ghoul = await self.get(telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for eat_human operation")
            raise ValueError("Ghoul not found")

        return await self.restore_hunger_from_eating(
            telegram_id, eat_humans=ghoul.eat_humans + 1
        )

    async def snap_finger(self, telegram_id: int) -> Ghoul:
        logger.debug(f"Called method snap_finger. Params: telegram_id={telegram_id}")

        ghoul = await self.get(telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for snap_finger operation")
            raise ValueError("Ghoul not found")

        logger.debug(f"Current snap count: {ghoul.snap_count}. Incrementing...")

        ghoul_updated = await self.ghoul_repository.upsert(
            telegram_id=telegram_id, snap_count=ghoul.snap_count + 1
        )

        logger.debug(
            f"Snap count updated successfully. New count: {ghoul_updated.snap_count}"
        )
        return ghoul_updated

    async def coffee(self, telegram_id: int, change: int = 1) -> Ghoul:
        logger.debug(
            f"Called method coffee. Params: telegram_id={telegram_id}, change={change}"
        )

        ghoul = await self.get(find_by=telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for coffee operation")
            raise ValueError("Ghoul not found")

        ghoul = await self.ghoul_repository.upsert(
            telegram_id=telegram_id, coffee_count=ghoul.coffee_count + change
        )

        return ghoul

    async def upgrade_kagune(
        self,
        telegram_id: int,
        kagune_type: Optional[KaguneType] = None,
        change: int = 1,
    ) -> Ghoul:
        logger.debug(
            f"Called method upgrade_kagune. Params: telegram_id={telegram_id}, "
            f"kagune_type={kagune_type}, change={change}"
        )

        ghoul = await self.get(find_by=telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for upgrade_kagune operation")
            raise ValueError("Ghoul not found")

        if kagune_type is None:
            owned = self.owned_kagune_types(ghoul)
            if len(owned) != 1:
                raise ValueError(
                    "kagune_type must be given explicitly when a ghoul owns "
                    "more than one kagune type"
                )
            kagune_type = owned[0]

        column = kagune_type.value["strength_column"]
        if getattr(ghoul, column) is None:
            raise ValueError(f"Ghoul does not own kagune type {kagune_type.value['name']}")

        updated = await self.ghoul_repository.increment_fields(
            telegram_id, **{column: change}
        )
        if not updated:
            raise ValueError("Ghoul not found during upgrade_kagune")

        return updated

    def owned_kagune_types(self, ghoul: Ghoul) -> List[KaguneType]:
        return [
            kagune_type
            for kagune_type in KaguneType
            if getattr(ghoul, kagune_type.value["strength_column"]) is not None
        ]

    def get_kagune_strength(self, ghoul: Ghoul, kagune_type: KaguneType) -> Optional[int]:
        return getattr(ghoul, kagune_type.value["strength_column"])

    def total_kagune_strength(self, ghoul: Ghoul) -> int:
        return sum(
            getattr(ghoul, kagune_type.value["strength_column"]) or 0
            for kagune_type in KaguneType
        )

    async def grant_kagune_type(
        self, telegram_id: int, kagune_type: KaguneType, initial_strength: int = 1
    ) -> Ghoul:
        ghoul = await self.get(telegram_id)
        if not ghoul:
            raise ValueError("Ghoul not found")

        column = kagune_type.value["strength_column"]
        if getattr(ghoul, column) is not None:
            raise ValueError(
                f"Ghoul already owns kagune type {kagune_type.value['name']}"
            )

        new_bit = (ghoul.kagune_type_bit or 0) | kagune_type.value["bit"]
        return await self.set_fields(
            telegram_id, kagune_type_bit=new_bit, **{column: initial_strength}
        )

    async def grant_all_kagune_types(
        self, telegram_id: int, initial_strength: int = 1
    ) -> Ghoul:
        ghoul = await self.get(telegram_id)
        if not ghoul:
            raise ValueError("Ghoul not found")

        updates: dict = {
            kagune_type.value["strength_column"]: initial_strength
            for kagune_type in KaguneType
            if getattr(ghoul, kagune_type.value["strength_column"]) is None
        }

        all_bits = sum(kagune_type.value["bit"] for kagune_type in KaguneType)
        return await self.set_fields(telegram_id, kagune_type_bit=all_bits, **updates)

    async def revoke_kagune_type(self, telegram_id: int, kagune_type: KaguneType) -> Ghoul:
        ghoul = await self.get(telegram_id)
        if not ghoul:
            raise ValueError("Ghoul not found")

        column = kagune_type.value["strength_column"]
        if getattr(ghoul, column) is None:
            raise ValueError(f"Ghoul does not own kagune type {kagune_type.value['name']}")

        if len(self.owned_kagune_types(ghoul)) <= 1:
            raise ValueError("Cannot remove the last remaining kagune type")

        new_bit = (ghoul.kagune_type_bit or 0) & ~kagune_type.value["bit"]
        return await self.set_fields(telegram_id, kagune_type_bit=new_bit, **{column: None})

    async def get_top_kagune(
        self, count=20, kagune_type: Optional[KaguneType] = None
    ) -> List[Ghoul]:
        logger.debug(
            f"Called method get_top_kagune. Params: count={count}, "
            f"kagune_type={kagune_type}"
        )
        top_kagune = await self.ghoul_repository.get_top_kagune(count, kagune_type)
        logger.debug(f"Retrieved top kagune list with {len(top_kagune)} entries")
        return top_kagune

    async def upsert(self, telegram_id: int, **kw: Any) -> Ghoul:
        logger.debug(
            f"Called method upsert. Params: telegram_id={telegram_id}, kwargs={kw}"
        )

        ghoul = await self.ghoul_repository.upsert(telegram_id=telegram_id, **kw)

        logger.debug(f"Ghoul upserted successfully. ID: {ghoul.id}")
        return ghoul

    async def register(self, telegram_id: int) -> RegisterGhoulType:
        logger.debug(f"Called method register. Params: telegram_id={telegram_id}")

        ghoul = await self.get(find_by=telegram_id)

        if ghoul:
            logger.warning(f"Registration failed: User {telegram_id} already exists")
            return RegisterGhoulType(ok=False, is_found=True)

        logger.debug("Generating initial kagune type for new ghoul")
        first_kagune = self._first_kagune()

        ghoul = await self.upsert(
            telegram_id=telegram_id,
            kagune_type_bit=first_kagune.value["bit"],
            **{first_kagune.value["strength_column"]: 1},
        )

        await self.user_repository.change_data(
            telegram_id=telegram_id, race_bit=Race.GHOUL.value["bit"]
        )

        logger.info(f"Successfully registered new ghoul: ID {ghoul.id}")
        return RegisterGhoulType(ok=True, is_found=True, ghoul=ghoul)

    async def get_top_snap(self, count=20) -> List[Ghoul]:
        return await self.ghoul_repository.get_top_snap(count)

    def _first_kagune(self) -> KaguneType:
        logger.debug("Called method _first_kagune")

        selected = random.choice(list(KaguneType))
        logger.debug(f"Selected kagune: {selected}")
        return selected

    def calculate_price_upgrade_kagune(self, kagune_strength: int) -> int:
        return int(
            KAGUNE_CONFIG.base_price * (kagune_strength**KAGUNE_CONFIG.exponent)
            + kagune_strength * KAGUNE_CONFIG.linear_multiplier
        )

    def calculate_power(self, ghoul: Ghoul) -> int:
        logger.debug(f"Called method calculate_power. Ghoul ID: {ghoul.id}")
        power = (
            ghoul.strength
            + ghoul.dexterity
            + ghoul.speed
            + ghoul.max_health
            + ghoul.regeneration
            + self.total_kagune_strength(ghoul)
        )
        logger.debug(f"Calculated power: {power}")
        return power

    def get_danger_rank(self, power: int) -> str:
        logger.debug(f"Called method get_danger_rank. Power: {power}")
        if power < 500:
            return "F"
        elif power < 1000:
            return "D"
        elif power < 1500:
            return "C"
        elif power < 2000:
            return "B"
        elif power < 3500:
            return "A"
        elif power < 5000:
            return "S"
        elif power < 7500:
            return "SS"
        elif power < 10000:
            return "SSS"
        else:
            return "SSS+"


__all__ = ["GhoulService"]
