from dataclasses import dataclass, field
from enum import Enum

from src.bot.game_configs import WORDLE_CONFIG


class LetterState(str, Enum):
    CORRECT = "correct"
    PRESENT = "present"
    ABSENT = "absent"


@dataclass
class GuessResult:
    word: str
    states: list[LetterState]

    @property
    def is_win(self) -> bool:
        return all(s == LetterState.CORRECT for s in self.states)

    def to_emoji(self) -> str:
        icons = {
            LetterState.CORRECT: "🟩",
            LetterState.PRESENT: "🟨",
            LetterState.ABSENT: "⬛",
        }
        return "".join(icons[s] for s in self.states)


@dataclass
class WordleGuessResult:
    """То, что роутер получает от сервиса после каждого хода"""

    png: bytes
    guess: GuessResult
    attempts_used: int
    attempts_left: int
    is_won: bool
    is_lost: bool
    target: str
    board_message_id: int | None


@dataclass
class _WordleGame:
    """Внутреннее состояние одной игровой сессии."""

    target: str
    guesses: list[GuessResult] = field(default_factory=list)
    board_message_id: int | None = None

    def __post_init__(self):
        self.target = self.target.upper()

    @property
    def attempts_used(self) -> int:
        return len(self.guesses)

    @property
    def attempts_left(self) -> int:
        return WORDLE_CONFIG.MAX_ATTEMPTS - self.attempts_used

    @property
    def is_won(self) -> bool:
        return bool(self.guesses) and self.guesses[-1].is_win

    @property
    def is_lost(self) -> bool:
        return self.attempts_used >= WORDLE_CONFIG.MAX_ATTEMPTS and not self.is_won

    @property
    def is_finished(self) -> bool:
        return self.is_won or self.is_lost

    def make_guess(self, word: str) -> GuessResult:
        word = word.upper()
        states = [LetterState.ABSENT] * WORDLE_CONFIG.WORD_LENGTH
        remaining: dict[str, int] = {}

        for i in range(WORDLE_CONFIG.WORD_LENGTH):
            if word[i] == self.target[i]:
                states[i] = LetterState.CORRECT
            else:
                remaining[self.target[i]] = remaining.get(self.target[i], 0) + 1

        for i in range(WORDLE_CONFIG.WORD_LENGTH):
            if states[i] == LetterState.CORRECT:
                continue
            if remaining.get(word[i], 0) > 0:
                states[i] = LetterState.PRESENT
                remaining[word[i]] -= 1

        result = GuessResult(word=word, states=states)
        self.guesses.append(result)
        return result
