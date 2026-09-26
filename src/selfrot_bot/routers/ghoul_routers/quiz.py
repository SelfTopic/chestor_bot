"""
/quiz: вопрос по «Токийскому гулю» из внешнего API (ctx.ghoul_quiz_service —
services/quiz.py, ghoul_quiz 0.2, https://chestor.site/api) и 4 варианта ответа кнопками.

Исправленный прод-баг: у прода кнопка несёт сам текст варианта
("quiz_answer_<id>_<вариант>"), поэтому вариант с "_" роняет разбор, а длинный
вариант (кириллица занимает 2 байта) не влезает в 64 байта callback_data, и
вопрос вообще не отправляется. Здесь кнопка несёт индекс варианта, а текст
берётся из самой клавиатуры сообщения под кнопкой. Ответ пользователю тот же.

Как у прода: состояние квиза (FSM) у каждого своё в каждом чате, "Play Again"
состояние не проверяет, а ответ и перезапуск не закрывают часики на кнопке
(callback.answer() прод зовёт только для "Quiz is not active.").
"""

import random
from typing import Any

from selfrot import (
    BaseRouter,
    CallbackPayload,
    InlineKeyboard,
    MessageHandler,
    State,
    States,
)
from selfrot.filter import Command, InState
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import DataCallbackQuery, InlineKeyboardMarkup, Message

from src.bot.game_configs import QUIZ_CONFIG

from ...context import AppContext
from ..types import TextMessage


class QuizStates(States):
    waiting_for_answer = State()
    quiz_completed = State()


class QuizAnswer(CallbackPayload, prefix="quiz_answer"):
    question_id: int
    option: int  # индекс варианта в клавиатуре сообщения


class QuizRestart(CallbackPayload, prefix="quiz_restart"):
    """Кнопка "Play Again"."""


async def new_question(ctx: AppContext[Any]) -> tuple[str, InlineKeyboardMarkup]:
    question = await ctx.ghoul_quiz_service.get_random_quiz()
    options = random.sample(question.answer_options, k=4)

    keyboard = InlineKeyboard(width=2)
    for index, option in enumerate(options):
        keyboard.button(option, QuizAnswer(question_id=question.id, option=index))

    return question.question, keyboard.markup()


class QuizHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("quiz")

    async def handle(self) -> None:
        await self.ctx.fsm.set(QuizStates.waiting_for_answer)
        text, keyboard = await new_question(self.ctx)
        await self.ctx.message.reply(text, reply_markup=keyboard)


class QuizAnswerHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    press = QuizAnswer.filter()
    query = InState(QuizStates.waiting_for_answer) & press

    def chosen_option(self, message: Message, index: int) -> str:
        markup = message.reply_markup
        buttons = [b for row in markup.inline_keyboard for b in row] if markup else []
        if not 0 <= index < len(buttons):
            raise ValueError("Quiz option is not in the keyboard")

        return buttons[index].text

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query

        await ctx.fsm.set(QuizStates.quiz_completed)

        message = callback.message
        if not isinstance(message, Message):
            raise ValueError("Callback query message is not of type Message")

        payload = self.press.parse(ctx)
        selected_option = self.chosen_option(message, payload.option)
        correct = await ctx.ghoul_quiz_service.get_answer_by_id(
            question_id=payload.question_id
        )

        restart = InlineKeyboard().button("Play Again", QuizRestart()).markup()
        text = (
            f"Вопрос: {correct.question} \nОтвет: {correct.answer}.\n"
            f"Твой выбор: {selected_option}\n"
        )

        if selected_option == correct.answer:
            award = QUIZ_CONFIG.award
            await ctx.user_service.plus_balance(
                telegram_id=callback.user.id,
                change_balance=award,
                log="ghoul quiz win",
            )
            text += f"Статус: верно\n\nПолучено CheSton: {award}"
        else:
            text += "Статус: неверно"

        await message.edit_text(text, reply_markup=restart)


class QuizNotActiveHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    """Ответ не в состоянии ожидания (уже ответил, или квиз начинал кто-то другой)."""

    query = QuizAnswer.filter()

    async def handle(self) -> None:
        await self.ctx.callback_query.answer("Quiz is not active.")


class QuizRestartHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = QuizRestart.filter()

    async def handle(self) -> None:
        ctx = self.ctx

        await ctx.fsm.set(QuizStates.waiting_for_answer)
        text, keyboard = await new_question(ctx)

        message = ctx.callback_query.message
        if not isinstance(message, Message):
            raise ValueError("Callback query message is not of type Message")

        await message.edit_text(text, reply_markup=keyboard)


class QuizRouter(BaseRouter[AppContext]):
    handlers = (
        QuizHandler,
        QuizAnswerHandler,
        QuizNotActiveHandler,
        QuizRestartHandler,
    )
