from typing import Any

from selfrot.types import Message

from ...context import AppContext
from ...services.battle import MobFight
from .battle_text import BattleMessage
from .battle_text_generator import BattleTextGenerator


async def answer_mob_battle(
    ctx: AppContext[Any], message: Message, fight: MobFight, *, what: str
) -> None:
    generator = BattleTextGenerator(dialog_service=ctx.dialog_service)
    await BattleMessage(generator, fight.report).answer(message, what=what)


def rewards_text(fight: MobFight) -> str:
    text = f"📈 Получено опыта: {fight.reward_level_progress:.2f}%"
    text += f"\n💰 Получено CheSton: {fight.reward_cheston}"
    if fight.reward_rc:
        text += f"\n♦️ Дополнительно найдено: {fight.reward_rc} RC-клеток!"
    return text
