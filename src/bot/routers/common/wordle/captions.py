"""Тексты wordle: подпись к доске после хода и итог партии."""

import html

from src.bot.game_configs import WORDLE_CONFIG
from src.bot.services.wikipedia import WikipediaSummary
from src.bot.types.wordle import WordleGuessResult


def attempts_word(n: int) -> str:
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


def guess_caption(result: WordleGuessResult, word: str) -> str:
    """Подпись к доске после хода."""
    if result.is_won:
        return (
            f"🎉 Вы угадали слово <b>{result.target}</b> "
            f"за {result.attempts_used} {attempts_word(result.attempts_used)}!\n"
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


def _word_html(word: str, summary: WikipediaSummary | None) -> str:
    """Загаданное слово: гиперссылка на статью в Википедии, а если статьи нет, жирным."""
    escaped = html.escape(word)
    if summary is None:
        return f"<b>{escaped}</b>"

    return f'<a href="{html.escape(summary.url)}">{escaped}</a>'


def _extract_block(summary: WikipediaSummary | None) -> str:
    return f"\n\n📖 {html.escape(summary.extract)}" if summary else ""


def win_text(
    result: WordleGuessResult, award: int, summary: WikipediaSummary | None
) -> str:
    return (
        f"🎉 Поздравляем! Слово {_word_html(result.target, summary)} угадано "
        f"за {result.attempts_used} {attempts_word(result.attempts_used)}!\n\n"
        f"Заработано {award} CheSton's\n"
        f"Сыграть ещё: /wordle{_extract_block(summary)}"
    )


def lose_text(result: WordleGuessResult, summary: WikipediaSummary | None) -> str:
    return (
        f"😔 Не получилось. Загаданное слово: {_word_html(result.target, summary)}\n"
        f"Попробовать ещё раз: /wordle{_extract_block(summary)}"
    )
