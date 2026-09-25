"""
Итог боя одним сообщением: rich (свёрнутый ход поединка), а если rich не прошёл,
то короткая текстовая сводка. Общее для боёв с мобом и дуэлей.

Текст рендерит прод-BattleTextGenerator как есть. Его build_rich_message() отдаёт
aiogram InputRichMessage; это та же схема Bot API, поэтому здесь она переводится в
selfrot InputRichMessage через JSON (model_dump → model_validate), а не
переписывается второй раз.
"""

from selfrot.types import InputRichMessage, Message

from src.bot.services import BattleTextGenerator
from src.bot.services.battle_engine.core import BattleResult, Fighter

from ..common.race_profile.rich import answer_rich_or_text


def battle_rich(
    generator: BattleTextGenerator,
    result: BattleResult,
    fighter_a: Fighter,
    fighter_b: Fighter,
    rank_a: str,
    rank_b: str,
) -> InputRichMessage:
    rendered = generator.build_rich_message(
        result, fighter_a, fighter_b, rank_a, rank_b
    )
    return InputRichMessage.model_validate(
        rendered.model_dump(mode="json", exclude_none=True)
    )


async def answer_battle(
    message: Message,
    generator: BattleTextGenerator,
    result: BattleResult,
    fighter_a: Fighter,
    fighter_b: Fighter,
    rank_a: str,
    rank_b: str,
    *,
    what: str,
) -> None:
    await answer_rich_or_text(
        message,
        battle_rich(generator, result, fighter_a, fighter_b, rank_a, rank_b),
        lambda: generator.build_plain_text(
            result, fighter_a, fighter_b, rank_a, rank_b
        ),
        what=what,
    )
