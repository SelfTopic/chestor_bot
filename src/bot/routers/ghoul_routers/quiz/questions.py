import random
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from selfrot import InlineKeyboard
from selfrot.exceptions import TelegramAPIError
from selfrot.types import (
    InlineKeyboardMarkup,
    InputRichBlock,
    InputRichBlockFooter,
    InputRichMessage,
    Message,
)

from src.bot.dialogs import Dialogs
from src.bot.exceptions import QuizModeDisabled
from src.bot.game_configs import QUIZ_CONFIG

from ....context import AppContext
from ...rich import paragraph
from .blocks import heading, media_block
from .payloads import QuizAnswer


class QuizMode(IntEnum):
    TEXT = 0
    WHOIS = 1
    TRUE_FALSE = 2


@dataclass
class AskedQuestion:
    blocks: list[InputRichBlock]
    keyboard: InlineKeyboardMarkup
    has_media: bool = False


def pick_mode() -> QuizMode:
    roll = random.random()
    if roll < QUIZ_CONFIG.whois_chance:
        return QuizMode.WHOIS
    if roll < QUIZ_CONFIG.whois_chance + QUIZ_CONFIG.true_false_chance:
        return QuizMode.TRUE_FALSE
    return QuizMode.TEXT


def options_keyboard(
    options: list[str], question_id: int, streak: int, mode: QuizMode, owner_id: int
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard(width=2)
    for index, option in enumerate(random.sample(options, k=min(4, len(options)))):
        keyboard.button(
            option,
            QuizAnswer(
                question_id=question_id,
                option=index,
                streak=streak,
                mode=mode,
                owner_id=owner_id,
            ),
        )
    return keyboard.markup()


async def ask(
    ctx: AppContext[Any], mode: QuizMode, streak: int, owner_id: int
) -> AskedQuestion:
    service = ctx.ghoul_quiz_service
    if mode is QuizMode.WHOIS:
        whois = await service.get_random_whois()
        keyboard = options_keyboard(whois.answer_options, whois.id, streak, mode, owner_id)
        blocks = [heading(ctx.text(Dialogs.quiz.whois_title())), media_block(whois.prompt_media)]
        return AskedQuestion(blocks, keyboard, has_media=True)

    if mode is QuizMode.TRUE_FALSE:
        statement = await service.get_random_true_false()
        keyboard = InlineKeyboard(width=2)
        for option, label in enumerate((Dialogs.quiz.true_button(), Dialogs.quiz.false_button())):
            keyboard.button(
                ctx.text(label),
                QuizAnswer(
                    question_id=statement.id,
                    option=option,
                    streak=streak,
                    mode=mode,
                    owner_id=owner_id,
                ),
            )
        blocks: list[InputRichBlock] = [
            heading(ctx.text(Dialogs.quiz.true_false_title())),
            paragraph(statement.statement),
        ]
        if statement.prompt_media is not None:
            blocks.append(media_block(statement.prompt_media))
        return AskedQuestion(blocks, keyboard.markup(), has_media=statement.prompt_media is not None)

    question = await service.get_random_quiz()
    keyboard = options_keyboard(question.answer_options, question.id, streak, mode, owner_id)
    return AskedQuestion([paragraph(question.question)], keyboard)


async def deliver(target: Message, asked: AskedQuestion, *, reply: bool) -> None:
    send = target.reply_rich_message if reply else target.answer_rich_message
    await send(InputRichMessage(blocks=asked.blocks), reply_markup=asked.keyboard)


async def send_question(
    ctx: AppContext[Any],
    target: Message,
    streak: int,
    owner_id: int,
    *,
    reply: bool,
    notice: str | None = None,
) -> None:
    try:
        asked = await ask(ctx, pick_mode(), streak, owner_id)
    except QuizModeDisabled:
        asked = await ask(ctx, QuizMode.TEXT, streak, owner_id)

    try:
        await deliver(target, with_notice(asked, notice), reply=reply)
    except TelegramAPIError:
        # Telegram не смог скачать картинку или видео по ссылке: вопрос без медиа не теряем.
        if not asked.has_media:
            raise
        asked = await ask(ctx, QuizMode.TEXT, streak, owner_id)
        await deliver(target, with_notice(asked, notice), reply=reply)


def with_notice(asked: AskedQuestion, notice: str | None) -> AskedQuestion:
    if notice is None:
        return asked
    # Сноской, а не первой строкой: результат повторяет блоки вопроса, а сгоревшая серия
    # относится только к этому вопросу.
    blocks = [*asked.blocks, InputRichBlockFooter(text=notice)]
    return AskedQuestion(blocks, asked.keyboard, asked.has_media)
