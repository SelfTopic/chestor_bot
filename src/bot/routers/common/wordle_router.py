import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.filters import Text, WordleGameFilter
from src.bot.game_configs import WORDLE_CONFIG
from src.bot.services import UserService, WordleService
from src.bot.types.wordle import WordleGuessResult

router = Router(name=__name__)
logger = logging.getLogger(__name__)


def _attempts_word(n: int) -> str:
    """Склонение слова 'попытка'."""
    if 11 <= n % 100 <= 14:
        return "попыток"
    match n % 10:
        case 1:
            return "попытку"
        case 2 | 3 | 4:
            return "попытки"
        case _:
            return "попыток"


def _build_caption(result: WordleGuessResult, word: str) -> str:
    if result.is_won:
        return (
            f"🎉 Вы угадали слово <b>{result.target}</b> "
            f"за {result.attempts_used} {_attempts_word(result.attempts_used)}!\n"
            f"{result.guess.to_emoji()}"
        )

    if result.is_lost:
        return f"😔 Попытки закончились.\nЗагаданное слово: <b>{result.target}</b>"

    return (
        f"{result.guess.to_emoji()}\n"
        f"Слово <b>{word.upper()}</b> — не то.\n"
        f"Попытка {result.attempts_used} из {WORDLE_CONFIG.MAX_ATTEMPTS}, "
        f"осталось {result.attempts_left}"
    )


async def _delete_board(
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> bool:
    """Удалить фото и подпись одного сообщения. Возвращает False при ошибке."""
    try:
        await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )
        return False
    except Exception:
        logger.debug("Failed to edit board message %d", message_id)
        return False


async def _notify_finish(
    message: Message, result: WordleGuessResult, user_service: UserService
) -> None:
    """Отправить финальное уведомление о победе или поражении."""

    assert message.from_user is not None
    if result.is_won:
        award = WORDLE_CONFIG.award
        await user_service.plus_balance(
            telegram_id=message.from_user.id,
            change_balance=award,
        )
        await message.answer(
            f"🎉 Поздравляем! Слово <b>{result.target}</b> угадано "
            f"за {result.attempts_used} {_attempts_word(result.attempts_used)}!\n\n"
            f"Заработано {award} CheSton's\n"
            "Сыграть ещё: /wordle",
            parse_mode="HTML",
        )
    elif result.is_lost:
        await message.answer(
            f"😔 Не получилось. Загаданное слово: <b>{result.target}</b>\n"
            "Попробовать ещё раз: /wordle",
            parse_mode="HTML",
        )


@router.message(Text("вордли"))
@router.message(Command("wordle"))
@inject
async def wordle_start_handler(
    message: Message,
    wordle_service: WordleService = Provide[Container.wordle_service],
) -> None:
    if not message.from_user:
        raise RuntimeError()

    user_id = message.from_user.id

    photo = wordle_service.get_current_board(telegram_id=user_id)
    if photo:
        sent = await message.reply_photo(
            photo=BufferedInputFile(file=photo, filename="wordle.png"),
            caption=(
                "У вас есть незавершённая игра.\n"
                "Введите слово из 5 букв чтобы продолжить."
            ),
        )
        wordle_service.set_board_message_id(user_id, sent.message_id)
        return

    photo = wordle_service.start_new_game(telegram_id=user_id)
    sent = await message.reply_photo(
        photo=BufferedInputFile(file=photo, filename="wordle.png"),
        caption=(
            "🟩 <b>Новая игра!</b>\n\n"
            "Угадайте слово из 5 букв за 6 попыток.\n"
            "🟩 — буква на своём месте\n"
            "🟨 — буква есть, но не там\n"
            "⬛ — буквы нет в слове"
        ),
        parse_mode="HTML",
    )
    wordle_service.set_board_message_id(user_id, sent.message_id)


@router.message(WordleGameFilter())
@inject
async def wordle_game_handler(
    message: Message,
    bot: Bot,
    wordle_service: WordleService = Provide[Container.wordle_service],
    user_service: UserService = Provide[Container.user_service],
) -> None:
    if not message.from_user or not message.text:
        raise RuntimeError()

    user_id = message.from_user.id
    word = message.text.strip()

    result = wordle_service.guess(telegram_id=user_id, word=word)
    if not result:
        return

    caption = _build_caption(result, word)
    photo = BufferedInputFile(file=result.png, filename="wordle.png")

    if result.board_message_id:
        edited = await _delete_board(
            bot,
            message.chat.id,
            result.board_message_id,
        )
        if edited:
            await message.delete()
            await _notify_finish(message, result, user_service)
            return

    try:
        await message.delete()

    except TelegramBadRequest:
        pass

    sent = await message.answer_photo(photo=photo, caption=caption, parse_mode="HTML")
    wordle_service.set_board_message_id(user_id, sent.message_id)
    await _notify_finish(message, result, user_service)
