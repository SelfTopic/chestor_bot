from typing import Any

from src.bot.dialogs import Dialogs, Line
from src.bot.game_configs import STATS
from src.bot.services.promo import (
    ChestonReward,
    CooldownResetReward,
    Granted,
    HealReward,
    HungerReward,
    LevelProgressReward,
    RcReward,
    StatReward,
)

from ..context import AppContext

STAT_LABELS = {key: f"{emoji}{label}" for label, key, emoji in STATS}


def reward_line(granted: Granted) -> Line:
    match granted.reward:
        case ChestonReward(amount=amount):
            return Dialogs.promo.reward.cheston(amount=amount)
        case RcReward(amount=amount):
            return Dialogs.promo.reward.rc(amount=amount)
        case LevelProgressReward(percent=percent):
            return Dialogs.promo.reward.progress(percent=percent)
        case HungerReward(percent=percent) if percent >= 100:
            return Dialogs.promo.reward.full_hunger()
        case HungerReward(percent=percent):
            return Dialogs.promo.reward.hunger(percent=percent)
        case HealReward():
            return Dialogs.promo.reward.heal()
        case CooldownResetReward():
            return Dialogs.promo.reward.cooldown_reset()
        case StatReward(stat=stat, amount=amount):
            if granted.capped_to is None:
                return Dialogs.promo.reward.stat(stat=STAT_LABELS[stat], amount=amount)
            return Dialogs.promo.reward.stat_capped(
                stat=STAT_LABELS[stat], amount=granted.capped_to
            )


def reward_lines(ctx: AppContext[Any], granted: list[Granted]) -> str:
    return "\n".join(ctx.text(reward_line(one)) for one in granted)
