from typing import Any

from src.bot.dialogs import Dialogs, Line
from src.bot.services.promo import ChestonReward, RcReward, Reward

from ..context import AppContext


def reward_line(reward: Reward) -> Line:
    match reward:
        case ChestonReward(amount=amount):
            return Dialogs.promo.reward.cheston(amount=amount)
        case RcReward(amount=amount):
            return Dialogs.promo.reward.rc(amount=amount)


def reward_lines(ctx: AppContext[Any], rewards: list[Reward]) -> str:
    return "\n".join(ctx.text(reward_line(reward)) for reward in rewards)
