import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from src.database.models import Ghoul

from ..game_configs import LEVEL_UP_CONFIG, STATS, stat_cap_for_level
from .dialog import DialogService
from .ghoul import GhoulService
from .user import UserService

logger = logging.getLogger(__name__)


@dataclass
class LevelUpResult:
    ghoul: Ghoul
    cheston_reward: int
    rc_reward: int
    notified: bool  # удалось ли отправить ЛС - награда выдаётся в любом случае


class LevelUpService:
    """Единая точка входа для любого повышения уровня - см. BATTLE_DESIGN.md.
    Сейчас ничего в проекте ещё не вызывает level_up() автоматически (нет
    level_progress/боевых наград) - это инфраструктура для будущих фич
    (награда за бой, /force_levelup для теста), которая уже сейчас
    гарантирует: подарок и повышение уровня применяются ДАЖЕ если ЛС
    отправить не удалось (частый случай - игрок играл только в чате, ни разу
    не открыв бота в личке)."""

    def __init__(
        self,
        user_service: UserService,
        ghoul_service: GhoulService,
        dialog_service: DialogService,
        bot: Bot,
    ) -> None:
        self.user_service = user_service
        self.ghoul_service = ghoul_service
        self.dialog_service = dialog_service
        self._bot = bot

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

        # Сначала ВСЕ изменения состояния - и только потом попытка уведомить.
        # Если ЛС не отправится, награда и уровень уже применены, откатывать
        # их не нужно и нельзя.
        await self.user_service.plus_balance(
            telegram_id=telegram_id,
            change_balance=cheston_reward,
            log=f"level up reward (level {new_level})",
        )
        final_ghoul = await self.ghoul_service.increment_fields(
            telegram_id, rc_money=rc_reward
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

    async def _notify(
        self,
        telegram_id: int,
        old_level: int,
        new_level: int,
        cheston_reward: int,
        rc_reward: int,
    ) -> bool:
        old_cap = stat_cap_for_level(old_level)
        new_cap = stat_cap_for_level(new_level)

        stat_lines = "\n".join(
            f"{emoji} {label}: {old_cap} -> {new_cap}" for label, _key, emoji in STATS
        )

        text = self.dialog_service.text(
            key="level_up_notify",
            level=new_level,
            cheston=cheston_reward,
            rc=rc_reward,
            stat_changes=stat_lines,
        )

        try:
            await self._bot.send_message(chat_id=telegram_id, text=text)
            return True
        except TelegramAPIError:
            # Самый частый случай - игрок ни разу не писал боту в личку
            # (только в чате), Telegram не разрешает инициировать диалог.
            # Награда уже выдана выше - это не повод её откатывать.
            logger.warning(
                f"Could not DM level-up notification to {telegram_id} - "
                f"reward still granted (level {new_level})",
                exc_info=True,
            )
            return False
        except Exception:
            logger.warning(
                f"Unexpected error sending level-up notification to {telegram_id}",
                exc_info=True,
            )
            return False


__all__ = ["LevelUpService", "LevelUpResult"]
