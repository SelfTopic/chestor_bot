from dataclasses import dataclass
from typing import Any

from ghoul_quiz import Media
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.game_configs import QUIZ_CONFIG

from ....context import AppContext
from .payloads import QuizAnswer
from .questions import QuizMode


@dataclass
class Verdict:
    answer: str
    choice: str
    correct: bool
    award_share: float = 1.0
    answer_media: Media | None = None


def chosen_option(message: Message, index: int) -> str:
    markup = message.reply_markup
    buttons = [b for row in markup.inline_keyboard for b in row] if markup else []
    if not 0 <= index < len(buttons):
        raise ValueError("Quiz option is not in the keyboard")

    return buttons[index].text


async def judge(ctx: AppContext[Any], message: Message, payload: QuizAnswer) -> Verdict:
    service = ctx.ghoul_quiz_service
    mode = QuizMode(payload.mode)

    if mode is QuizMode.TRUE_FALSE:
        truth = await service.get_true_false_answer(payload.question_id)
        labels = (ctx.text(Dialogs.quiz.true_button()), ctx.text(Dialogs.quiz.false_button()))
        answer = labels[0] if truth.correct else labels[1]
        choice = labels[payload.option]
        return Verdict(answer, choice, choice == answer, QUIZ_CONFIG.true_false_share)

    choice = chosen_option(message, payload.option)
    if mode is QuizMode.WHOIS:
        whois = await service.get_whois_answer(payload.question_id)
        return Verdict(whois.answer, choice, choice == whois.answer)

    text = await service.get_answer_by_id(question_id=payload.question_id)
    return Verdict(text.answer, choice, choice == text.answer, answer_media=text.answer_media)
