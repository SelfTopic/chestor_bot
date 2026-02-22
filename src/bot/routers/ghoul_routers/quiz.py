import random

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...game_configs import QUIZ_CONFIG
from ...services import GhoulQuizService, UserService

router = Router(name=__name__)


class QuizStates(StatesGroup):
    waiting_for_answer = State()
    quiz_completed = State()


@router.message(Command("quiz"))
@inject
async def quiz_handler(
    message: Message,
    state: FSMContext,
    ghoul_quiz_service: GhoulQuizService = Provide[Container.ghoul_quiz_service],
):
    await state.set_state(QuizStates.waiting_for_answer)
    question = await ghoul_quiz_service.get_random_quiz()
    options = random.choices(question.answer_options, k=4)

    builder = InlineKeyboardBuilder()

    for option in options:
        builder.button(text=option, callback_data=f"quiz_answer_{question.id}_{option}")
    builder.adjust(2)

    await message.reply(text=question.question, reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data.startswith("quiz_answer_"))
@inject
async def quiz_answer_handler(
    callback_query: CallbackQuery,
    state: FSMContext,
    ghoul_quiz_service: GhoulQuizService = Provide[Container.ghoul_quiz_service],
    user_service: UserService = Provide[Container.user_service],
):
    current_state = await state.get_state()
    if current_state != QuizStates.waiting_for_answer.state:
        await callback_query.answer("Quiz is not active.")
        return

    await state.set_state(QuizStates.quiz_completed)
    if not callback_query.data:
        raise ValueError("Callback data is missing")

    id, selected_option = callback_query.data[len("quiz_answer_") :].split("_")

    correct_answer = await ghoul_quiz_service.get_answer_by_id(question_id=int(id))

    restart_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Play Again", callback_data="quiz_restart")]
        ]
    )
    if not isinstance(callback_query.message, Message):
        raise ValueError("Callback query message is not of type Message")

    if selected_option == correct_answer.answer:
        award = QUIZ_CONFIG.award
        await user_service.plus_balance(
            telegram_id=callback_query.from_user.id, change_balance=award
        )
        await callback_query.message.edit_text(
            text=f"Вопрос: {correct_answer.question} \nОтвет: {correct_answer.answer}.\nТвой выбор: {selected_option}\nСтатус: верно\n\nПолучено CheSton: {award}",
            reply_markup=restart_keyboard,
        )

    else:
        await callback_query.message.edit_text(
            text=f"Вопрос: {correct_answer.question} \nОтвет: {correct_answer.answer}.\nТвой выбор: {selected_option}\nСтатус: неверно",
            reply_markup=restart_keyboard,
        )


@router.callback_query(lambda c: c.data == "quiz_restart")
@inject
async def quiz_restart_handler(
    callback_query: CallbackQuery,
    state: FSMContext,
    ghoul_quiz_service: GhoulQuizService = Provide[Container.ghoul_quiz_service],
):
    await state.set_state(QuizStates.waiting_for_answer)
    question = await ghoul_quiz_service.get_random_quiz()
    options = random.sample(question.answer_options, k=4)
    builder = InlineKeyboardBuilder()

    for option in options:
        builder.button(text=option, callback_data=f"quiz_answer_{question.id}_{option}")
    builder.adjust(2)

    if not isinstance(callback_query.message, Message):
        raise ValueError("Callback query message is not of type Message")

    await callback_query.message.edit_text(
        text=question.question, reply_markup=builder.as_markup()
    )
