"""
Итог боя одним сообщением: rich (свёрнутый ход поединка), а если rich не прошёл,
то короткая текстовая сводка. Общее для боёв с мобом и дуэлей.

Текст рендерит BattleTextGenerator (battle_text_generator.py).
"""

from dataclasses import dataclass
from functools import cached_property

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError
from selfrot.types import InlineKeyboardMarkup, InputRichMessage, Message

from ...services.battle import FightReport
from ..rich import answer_rich_or_text
from .battle_text_generator import BattleTextGenerator


@dataclass
class BattleMessage:
    """Итог одного боя. Оба вида строятся по разу, даже если чатов несколько, а
    текст — только если rich где-то не прошёл."""

    generator: BattleTextGenerator
    report: FightReport

    @cached_property
    def rich(self) -> InputRichMessage:
        r = self.report
        return self.generator.build_rich_message(
            r.result, r.fighter_a, r.fighter_b, r.rank_a, r.rank_b
        )

    @cached_property
    def plain_text(self) -> str:
        r = self.report
        return self.generator.build_plain_text(
            r.result, r.fighter_a, r.fighter_b, r.rank_a, r.rank_b
        )

    async def answer(self, message: Message, *, what: str) -> None:
        """В чат сообщения (бой с мобом)."""
        await answer_rich_or_text(message, self.rich, lambda: self.plain_text, what=what)

    async def send(
        self, bot: Bot, chat_id: int, reply_markup: InlineKeyboardMarkup | None = None
    ) -> Message | None:
        """В чат по id (дуэль). None — не доставлено ни rich, ни текстом."""
        try:
            return await bot.send_rich_message(
                chat_id=chat_id, rich_message=self.rich, reply_markup=reply_markup
            )
        except TelegramAPIError:
            pass
        try:
            return await bot.send_message(
                chat_id=chat_id, text=self.plain_text, reply_markup=reply_markup
            )
        except TelegramAPIError:
            return None
