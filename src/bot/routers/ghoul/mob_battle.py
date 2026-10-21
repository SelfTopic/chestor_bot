from typing import Any

from selfrot.types import Message

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ...services.battle import MobFight
from .battle_text import BattleMessage
from .battle_text_generator import BattleTextGenerator


async def answer_mob_battle(
    ctx: AppContext[Any], message: Message, fight: MobFight, *, what: str
) -> None:
    generator = BattleTextGenerator(dialog_service=ctx.dialog_service)
    await BattleMessage(generator, fight.report).answer(message, what=what)


def rewards_text(ctx: AppContext[Any], fight: MobFight) -> str:
    rewards = ctx.text(
        Dialogs.mob.rewards(
            progress=f"{fight.reward_level_progress:.2f}", cheston=fight.reward_cheston
        )
    )
    if fight.reward_rc:
        rewards += "\n" + ctx.text(Dialogs.mob.rc_found(rc=fight.reward_rc))
    return rewards
