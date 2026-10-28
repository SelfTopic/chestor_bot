from ghoul_quiz import Media
from selfrot import BaseRouter, InlineKeyboard, MessageHandler, State, States
from selfrot.exceptions import TelegramAPIError
from selfrot.filter import Command, HasUser, InState, Text
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import (
    DataCallbackQuery,
    InlineKeyboardMarkup,
    InputRichBlock,
    InputRichMessage,
    Message,
)

from src.bot.dialogs import Dialogs
from src.bot.game_configs import QUIZ_CONFIG

from ....context import AppContext
from ...types import TextUserMessage
from .blocks import media_block, paragraphs, question_blocks
from .payloads import QuizAnswer, QuizRestart
from .questions import send_question
from .verdict import judge


class QuizStates(States):
    waiting_for_answer = State()
    quiz_completed = State()


def callback_message(ctx: AppContext[DataCallbackQuery]) -> Message:
    message = ctx.callback_query.message
    if not isinstance(message, Message):
        raise ValueError("Callback query message is not of type Message")
    return message


class QuizHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = (
        Command("quiz")
        | Text("квиз", ignore_case=True)
        | Text("викторина", ignore_case=True)
        | Text("quiz", ignore_case=True)
    ) & HasUser()

    async def handle(self) -> None:
        await self.ctx.fsm.set(QuizStates.waiting_for_answer)
        await send_question(
            self.ctx,
            self.ctx.message,
            streak=0,
            owner_id=self.ctx.message.user.id,
            edit=False,
        )


class QuizAnswerHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    press = QuizAnswer.filter().pressed_by("owner_id")
    query = InState(QuizStates.waiting_for_answer) & press

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query

        await ctx.fsm.set(QuizStates.quiz_completed)

        message = callback_message(ctx)
        payload = self.press.parse(ctx)
        verdict = await judge(ctx, message, payload)

        if verdict.correct:
            streak = payload.streak + 1
            award = QUIZ_CONFIG.award(streak, verdict.award_share)
            await ctx.user_service.plus_balance(
                telegram_id=callback.user.id,
                change_balance=award,
                log="ghoul quiz win",
            )
            status = Dialogs.quiz.correct(
                award=award,
                streak=streak,
                multiplier=f"{QUIZ_CONFIG.multiplier(streak):g}",
                minutes=QUIZ_CONFIG.streak_ttl_seconds // 60,
            )
        elif payload.streak:
            streak = 0
            status = Dialogs.quiz.wrong_streak(streak=payload.streak)
        else:
            streak = 0
            status = Dialogs.quiz.wrong()

        play_again = ctx.text(Dialogs.quiz.play_again())
        restart = (
            InlineKeyboard()
            .button(play_again, QuizRestart(owner_id=callback.user.id))
            .markup()
        )

        result = ctx.text(
            Dialogs.quiz.result(
                answer=verdict.answer, choice=verdict.choice, status=ctx.text(status)
            )
        )
        blocks = [*question_blocks(message), *paragraphs(result)]
        rich = await self.show_result(message, blocks, verdict.answer_media, restart)
        if streak:
            await ctx.quiz_streak_service.hold(
                callback.user.id,
                message.chat.id,
                message.message_id,
                rich.model_dump_json(exclude_none=True),
                streak,
            )

    async def show_result(
        self,
        message: Message,
        blocks: list[InputRichBlock],
        answer_media: Media | None,
        restart: InlineKeyboardMarkup,
    ) -> InputRichMessage:
        if answer_media is not None:
            illustrated = InputRichMessage(blocks=[*blocks, media_block(answer_media)])
            try:
                await message.edit_text(rich_message=illustrated, reply_markup=restart)
            except TelegramAPIError:
                # Telegram не смог скачать иллюстрацию по ссылке: результат всё равно покажем.
                pass
            else:
                return illustrated

        plain = InputRichMessage(blocks=blocks)
        await message.edit_text(rich_message=plain, reply_markup=restart)
        return plain


class QuizNotActiveHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = QuizAnswer.filter().pressed_by("owner_id")

    async def handle(self) -> None:
        await self.ctx.callback_query.answer(self.ctx.text(Dialogs.quiz.not_active()))


class QuizRestartHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = QuizRestart.filter().pressed_by("owner_id")

    async def handle(self) -> None:
        ctx = self.ctx
        message = callback_message(ctx)

        held = await ctx.quiz_streak_service.take(
            ctx.callback_query.user.id, message.message_id
        )
        streak = held.streak if held and held.alive else 0
        notice = None
        if held and not held.alive:
            # Тикер ещё не дошёл до этого сообщения, но срок серии уже вышел.
            notice = ctx.text(Dialogs.quiz.streak_expired(streak=held.streak))

        await ctx.fsm.set(QuizStates.waiting_for_answer)
        await send_question(
            ctx, message, streak, ctx.callback_query.user.id, edit=True, notice=notice
        )


class QuizForeignPressHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = QuizAnswer.filter() | QuizRestart.filter()

    async def handle(self) -> None:
        await self.ctx.callback_query.answer(self.ctx.text(Dialogs.quiz.not_yours()))


class QuizRouter(BaseRouter[AppContext]):
    handlers = (
        QuizHandler,
        QuizAnswerHandler,
        QuizNotActiveHandler,
        QuizRestartHandler,
        QuizForeignPressHandler,
    )
