from typing import Any

from src.bot.dialogs import Dialogs, Line, LineText
from src.bot.dialogs.vocab import stat_label
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

def reward_line(text: LineText, granted: Granted) -> Line:
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
                return Dialogs.promo.reward.stat(stat=stat_label(text, stat), amount=amount)
            return Dialogs.promo.reward.stat_capped(
                stat=stat_label(text, stat), amount=granted.capped_to
            )


def reward_lines(ctx: AppContext[Any], granted: list[Granted]) -> str:
    return "\n".join(ctx.text(reward_line(ctx.text, one)) for one in granted)
