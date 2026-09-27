import html
from typing import Any

from src.bot.dialogs import Dialogs
from src.bot.game_configs import WORDLE_CONFIG
from src.bot.services.wikipedia import WikipediaSummary
from src.bot.types.wordle import WordleGuessResult

from ....context import AppContext


def attempts_word(n: int) -> str:
    if 11 <= n % 100 <= 14:
        return "попыток"
    match n % 10:
        case 1:
            return "попытку"
        case 2 | 3 | 4:
            return "попытки"
        case _:
            return "попыток"


def guess_caption(ctx: AppContext[Any], result: WordleGuessResult, word: str) -> str:
    if result.is_won:
        line = Dialogs.wordle.guess.won(
            word=result.target,
            attempts=result.attempts_used,
            attempts_word=attempts_word(result.attempts_used),
            board=result.guess.to_emoji(),
        )
    elif result.is_lost:
        line = Dialogs.wordle.guess.lost(word=result.target)
    else:
        line = Dialogs.wordle.guess.miss(
            board=result.guess.to_emoji(),
            word=word.upper(),
            used=result.attempts_used,
            max_attempts=WORDLE_CONFIG.MAX_ATTEMPTS,
            left=result.attempts_left,
        )
    return ctx.text(line)


def _word_html(word: str, summary: WikipediaSummary | None) -> str:
    escaped = html.escape(word)
    if summary is None:
        return f"<b>{escaped}</b>"

    return f'<a href="{html.escape(summary.url)}">{escaped}</a>'


def _extract_block(ctx: AppContext[Any], summary: WikipediaSummary | None) -> str:
    if summary is None:
        return ""
    return ctx.text(Dialogs.wordle.wiki_extract(extract=html.escape(summary.extract)))


def win_text(
    ctx: AppContext[Any],
    result: WordleGuessResult,
    award: int,
    summary: WikipediaSummary | None,
) -> str:
    return ctx.text(
        Dialogs.wordle.win(
            word=_word_html(result.target, summary),
            attempts=result.attempts_used,
            attempts_word=attempts_word(result.attempts_used),
            award=award,
            wiki=_extract_block(ctx, summary),
        )
    )


def lose_text(
    ctx: AppContext[Any], result: WordleGuessResult, summary: WikipediaSummary | None
) -> str:
    return ctx.text(
        Dialogs.wordle.lose(
            word=_word_html(result.target, summary), wiki=_extract_block(ctx, summary)
        )
    )
