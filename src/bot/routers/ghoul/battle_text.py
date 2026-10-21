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
        await answer_rich_or_text(message, self.rich, lambda: self.plain_text, what=what)

    async def send(
        self, bot: Bot, chat_id: int, reply_markup: InlineKeyboardMarkup | None = None
    ) -> Message | None:
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
