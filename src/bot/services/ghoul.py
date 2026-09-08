import logging
import random
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple, Union

from aiogram.types import Message

from src.database.models import Ghoul

from ..game_configs import EAT_HUMAN_CONFIG, KAGUNE_CONFIG
from ..repositories import ScheduledNotificationRepository
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
    ) -> None:
        super().__init__(
            user_repository, ghoul_repository, user_cooldown_repository, chat_repository
        )
        # Опционально - без него materialize_passive_stats просто не
        # планирует пуши (тише для тестов/прочих мест, где это не нужно).
        self.notification_repository = notification_repository

    async def get(self, find_by: Union[Message, int]) -> Optional[Ghoul]:
        logger.debug(
            f"Called method get. Params: find_by={find_by if not isinstance(find_by, Message) else 'Message'}"
        )

        search_parameter = find_by

        if isinstance(find_by, Message):
            logger.debug("Received Message object, extracting user ID")
            if not find_by.from_user:
                logger.warning("Message has no from_user attribute")
                return None
            search_parameter = find_by.from_user.id

        if isinstance(search_parameter, int):
            if search_parameter > 666000:
                logger.debug(f"Looking up by Telegram ID: {search_parameter}")
                ghoul = await self.ghoul_repository.get(search_parameter)
            else:
                logger.debug(f"Looking up by custom ID: {search_parameter}")
                ghoul = await self.ghoul_repository.get_by_id(search_parameter)

            logger.debug(f"Ghoul found: {ghoul is not None}")
            if ghoul:
                ghoul = await self.materialize_passive_stats(ghoul)
            return ghoul

        logger.error(f"Invalid parameter type: {type(search_parameter)}")
        raise ValueError(f"Invalid type parameter: {type(search_parameter)}")

    async def materialize_passive_stats(self, ghoul: Ghoul) -> Ghoul:
        """Досчитывает голод/здоровье на текущий момент (ленивый расчёт,
        см. BATTLE_DESIGN.md) и, если что-то изменилось, сохраняет.

        Смерть от голода (would_starve) сюда пока не подключена - это
        отдельный шаг, требующий готовой логики сброса гуля."""

        now = utcnow_naive()

        new_hunger, new_hunger_at, _would_starve = compute_hunger(
            hunger=ghoul.hunger,
            hunger_updated_at=ghoul.hunger_updated_at,
            is_kakuja=ghoul.is_kakuja,
            now=now,
        )

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

        # Расписание пересчитывается всегда, а не только когда голод/хп
        # реально сдвинулись этим вызовом - иначе правка админом через
        # /set_stat не переставит уже стоящий пуш (см. коммент к
        # sync_notification_schedule).
        if self.notification_repository is not None:
            await self.sync_notification_schedule(result, now=now)

        return result

    async def sync_notification_schedule(self, ghoul: Ghoul, now: datetime) -> None:
        """Пере-планирует пуши "здоровье полное"/"голод дошёл до порога" по
        ТЕКУЩЕМУ состоянию гуля. Вызывается при каждом чтении гуля и при
        каждом осознанном изменении голода/хп - см. BATTLE_DESIGN.md,
        "Механизм regen/hunger" (дисциплину легко забыть в будущей фиче)."""

        if self.notification_repository is None:
            return

        hp_per_hour = health_regen_per_hour(
            regeneration=ghoul.regeneration,
            hunger=ghoul.hunger,
            kagune_type_bit=ghoul.kagune_type_bit or 0,
            is_kakuja=ghoul.is_kakuja,
        )
        hours_to_full = hours_until_full_health(ghoul.health, ghoul.max_health, hp_per_hour)

        if not hours_to_full:  # None (никогда) или 0.0 (уже полное) - не планируем
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

        if threshold is None:
            await self.notification_repository.delete(
                ghoul.telegram_id, NotificationType.HUNGER_THRESHOLD
            )
        else:
            hours_to_threshold = hours_until_hunger_threshold(
                ghoul.hunger, ghoul.is_kakuja, threshold
            )
            await self.notification_repository.schedule(
                telegram_id=ghoul.telegram_id,
                notification_type=NotificationType.HUNGER_THRESHOLD,
                fire_at=now + timedelta(hours=hours_to_threshold),
                threshold=threshold,
            )

    async def eat_human(self, telegram_id: int) -> Tuple[Ghoul, int]:
        """Фаза 3a ("Поесть человека" в BATTLE_DESIGN.md) - без риска
        нападения моба, это 3b, требует боевого движка. Кулдаун (1 сутки)
        проверяется в роутере через CooldownService, не здесь.

        Возвращает (обновлённый_гуль, сколько_голода_восстановлено)."""

        logger.debug(f"Called method eat_human. Params: telegram_id={telegram_id}")

        ghoul = await self.get(telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for eat_human operation")
            raise ValueError("Ghoul not found")

        restore = EAT_HUMAN_CONFIG.hunger_restore
        new_hunger = apply_hunger_restore(ghoul.hunger, restore)

        updated_ghoul = await self.ghoul_repository.upsert(
            telegram_id=telegram_id,
            hunger=new_hunger,
            hunger_updated_at=utcnow_naive(),
            eat_humans=ghoul.eat_humans + 1,
        )

        # Голод только что осознанно изменился - расписание пуша по голоду
        # обязано пересчитаться сейчас же, а не ждать следующего чтения.
        await self.sync_notification_schedule(updated_ghoul, now=utcnow_naive())

        logger.debug(
            f"eat_human: hunger {ghoul.hunger}->{new_hunger} (+{restore}), "
            f"eat_humans={updated_ghoul.eat_humans}"
        )

        return updated_ghoul, restore

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

    async def upgrade_kagune(self, telegram_id: int, change: int = 1) -> Ghoul:
        logger.debug(
            f"Called method upsert. Params: telegram_id={telegram_id}, change={change}"
        )

        ghoul = await self.get(find_by=telegram_id)

        if not ghoul:
            logger.error("Ghoul not found for upgarde_kagune operation")
            raise ValueError("Ghoul not found")

        ghoul = await self.ghoul_repository.upsert(
            telegram_id=telegram_id, kagune_strength=ghoul.kagune_strength + change
        )

        return ghoul

    async def get_top_kagune(self, count=20) -> List[Ghoul]:
        logger.debug(f"Called method get_top_kagune. Params: count={count}")
        top_kagune = await self.ghoul_repository.get_top_kagune(count)
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

        ghoul = await self.upsert(telegram_id=telegram_id, kagune_type_bit=first_kagune)

        await self.user_repository.change_data(
            telegram_id=telegram_id, race_bit=Race.GHOUL.value["bit"]
        )

        logger.info(f"Successfully registered new ghoul: ID {ghoul.id}")
        return RegisterGhoulType(ok=True, is_found=True, ghoul=ghoul)

    async def get_top_snap(self, count=20) -> List[Ghoul]:
        return await self.ghoul_repository.get_top_snap(count)

    def _first_kagune(self) -> int:
        logger.debug("Called method _first_kagune")

        bits = [kagune.value["bit"] for kagune in KaguneType]
        logger.debug(f"Available kagune bits: {bits}")

        selected = random.choice(bits)
        logger.debug(f"Selected kagune bit: {selected}")
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
            + ghoul.kagune_strength
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
