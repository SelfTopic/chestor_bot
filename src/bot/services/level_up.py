import logging
from dataclasses import dataclass, field

from src.bot.dialogs import Dialogs
from src.bot.game_configs import LEVEL_UP_CONFIG, STATS, stat_cap_for_level
from src.bot.services import DialogService, GhoulService, UserService
from src.bot.utils import apply_level_progress
from src.database.models import Ghoul

from .notify import NotifyError, Notifier

logger = logging.getLogger(__name__)


@dataclass
class LevelUpResult:
    ghoul: Ghoul
    cheston_reward: int
    rc_reward: int
    notified: bool


@dataclass
class ProgressResult:
    ghoul: Ghoul
    progress: float
    levels_gained: int
    level_up_results: list[LevelUpResult] = field(default_factory=list)


class LevelUpService:
    def __init__(
        self,
        user_service: UserService,
        ghoul_service: GhoulService,
        dialog_service: DialogService,
        notifier: Notifier,
    ) -> None:
        self.user_service = user_service
        self.ghoul_service = ghoul_service
        self.dialog_service = dialog_service
        self._notifier = notifier

    async def level_up(self, telegram_id: int) -> LevelUpResult:
        old_ghoul = await self.ghoul_service.get(telegram_id)
        if not old_ghoul:
            raise ValueError("Ghoul not found")

        old_level = old_ghoul.level

        new_ghoul = await self.ghoul_service.increment_fields(telegram_id, level=1)
        if not new_ghoul:
            raise ValueError("Ghoul not found during level up")

        new_level = new_ghoul.level

        cheston_reward = LEVEL_UP_CONFIG.cheston_reward(new_level)
        rc_reward = LEVEL_UP_CONFIG.rc_reward(new_level)

        # Сначала все изменения, потом уведомление: если ЛС не дойдёт, уровень и награда уже
        # выданы.
        await self.user_service.plus_balance(
            telegram_id=telegram_id,
            change_balance=cheston_reward,
            log=f"level up reward (level {new_level})",
        )
        final_ghoul = await self.ghoul_service.increment_fields(
            telegram_id, rc_money=rc_reward, lifetime_rc_earned=rc_reward
        )
        if not final_ghoul:
            raise ValueError("Ghoul not found while granting RC reward")

        notified = await self._notify(
            telegram_id, old_level, new_level, cheston_reward, rc_reward
        )

        return LevelUpResult(
            ghoul=final_ghoul,
            cheston_reward=cheston_reward,
            rc_reward=rc_reward,
            notified=notified,
        )

    async def add_progress(self, telegram_id: int, delta: float) -> ProgressResult:
        ghoul = await self.ghoul_service.get(telegram_id)
        if not ghoul:
            raise ValueError("Ghoul not found")

        new_progress, levels_gained = apply_level_progress(ghoul.level_progress, delta)

        updated_ghoul = await self.ghoul_service.set_fields(
            telegram_id, level_progress=new_progress
        )

        level_up_results = [
            await self.level_up(telegram_id) for _ in range(levels_gained)
        ]

        return ProgressResult(
            ghoul=level_up_results[-1].ghoul if level_up_results else updated_ghoul,
            progress=new_progress,
            levels_gained=levels_gained,
            level_up_results=level_up_results,
        )

    async def _notify(
        self,
        telegram_id: int,
        old_level: int,
        new_level: int,
        cheston_reward: int,
        rc_reward: int,
    ) -> bool:
        stat_lines = "\n".join(
            f"{emoji} {label}: {stat_cap_for_level(old_level, key)} -> "
            f"{stat_cap_for_level(new_level, key)}"
            for label, key, emoji in STATS
        )

        text = self.dialog_service.text(
            Dialogs.notify.level_up(
                level=new_level,
                cheston=cheston_reward,
                rc=rc_reward,
                stat_changes=stat_lines,
            )
        )

        try:
            await self._notifier.send_message(telegram_id, text)
            return True
        except NotifyError:
            logger.warning(
                f"Could not DM level-up notification to {telegram_id} - "
                f"reward still granted (level {new_level})",
                exc_info=True,
            )
            return False


__all__ = ["LevelUpService", "LevelUpResult", "ProgressResult"]
