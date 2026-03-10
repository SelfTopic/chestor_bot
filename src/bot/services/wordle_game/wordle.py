import logging
import random
from typing import Optional

from src.bot.game_configs import WORDLE_CONFIG
from src.bot.types.wordle import WordleGuessResult, _WordleGame

from .renderer import _render_board

logger = logging.getLogger(__name__)

words_file = open("/src/assets/data/wordle/words.txt")
WORD_LIST: list[str] = words_file.readlines()
words_file.close()
WORD_LIST = [w.upper() for w in WORD_LIST if len(w) == WORDLE_CONFIG.WORD_LENGTH]


class WordleService:
    """
    Сервис Wordle-игры.

    Регистрируется как Singleton в Container — хранит все сессии
    в памяти процесса. При перезапуске бота активные игры сбрасываются.
    """

    def __init__(self) -> None:
        self._sessions: dict[int, _WordleGame] = {}
        logger.info("WordleService initialized")

    def start_new_game(self, telegram_id: int) -> bytes:
        """Начать новую игру. Возвращает PNG пустого поля."""
        word = random.choice(WORD_LIST)
        game = _WordleGame(target=word)
        self._sessions[telegram_id] = game
        logger.debug(f"New wordle game for user {telegram_id}, target={word}")
        return _render_board(game)

    def has_active_game(self, telegram_id: int) -> bool:
        game = self._sessions.get(telegram_id)
        return game is not None and not game.is_finished

    def get_current_board(self, telegram_id: int) -> Optional[bytes]:
        """PNG текущего поля или None если нет активной игры."""
        game = self._sessions.get(telegram_id)
        if not game:
            return None
        return _render_board(game)

    def set_board_message_id(self, telegram_id: int, message_id: int) -> None:
        """Сохранить message_id отправленной доски для последующего редактирования."""
        game = self._sessions.get(telegram_id)
        if game:
            game.board_message_id = message_id

    def get_board_message_id(self, telegram_id: int) -> int | None:
        """Вернуть message_id доски или None если ещё не отправлена."""
        game = self._sessions.get(telegram_id)
        return game.board_message_id if game else None

    def forfeit(self, telegram_id: int) -> Optional[str]:
        """Сдаться. Возвращает загаданное слово или None если игры нет."""
        game = self._sessions.pop(telegram_id, None)
        return game.target if game else None

    def guess(self, telegram_id: int, word: str) -> Optional[WordleGuessResult]:
        """
        Сделать попытку.

        Returns:
            WordleGuessResult если ход принят,
            None если нет активной игры для этого пользователя.
        Raises:
            ValueError: неверная длина слова или некириллические символы.
        """
        game = self._sessions.get(telegram_id)
        if not game or game.is_finished:
            return None

        word = word.upper().strip()

        if len(word) != WORDLE_CONFIG.WORD_LENGTH:
            raise ValueError(
                f"Слово должно содержать {WORDLE_CONFIG.WORD_LENGTH} букв."
            )

        if not all("А" <= ch <= "Я" or ch == "Ё" for ch in word):
            raise ValueError("Используйте только русские буквы.")

        result = game.make_guess(word)

        if game.is_finished:
            self._sessions.pop(telegram_id, None)

        png = _render_board(game)

        return WordleGuessResult(
            png=png,
            guess=result,
            attempts_used=game.attempts_used,
            attempts_left=game.attempts_left,
            is_won=game.is_won,
            is_lost=game.is_lost,
            target=game.target,
            board_message_id=game.board_message_id,
        )
