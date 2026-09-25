"""
Бой с мобом на стороне Telegram: общий для "бить моба" (mob_fight.py) и засады в
"сожрать человека" (eat_human.py). Сам бой, награды и история —
BattleService.fight_mob; здесь только как их показать.
"""

from typing import Any

from selfrot.types import Message

from ...context import AppContext
from ...services.battle import MobFight
from .battle_text import BattleMessage


async def answer_mob_battle(
    ctx: AppContext[Any], message: Message, fight: MobFight, *, what: str
) -> None:
    await BattleMessage(ctx.battle_text_generator, fight.report).answer(message, what=what)


def rewards_text(fight: MobFight) -> str:
    """Строки наград за победу, одинаковые у обоих видов боя."""
    text = f"📈 Получено опыта: {fight.reward_level_progress:.2f}%"
    text += f"\n💰 Получено CheSton: {fight.reward_cheston}"
    if fight.reward_rc:
        text += f"\n♦️ Дополнительно найдено: {fight.reward_rc} RC-клеток!"
    return text
