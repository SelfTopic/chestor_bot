import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from ghoul_quiz import (
    DEFAULT_BASE_URL,
    Answer,
    GhoulQuizAPI,
    Question,
    TrueFalseAnswer,
    TrueFalseQuestion,
    WhoisAnswer,
    WhoisQuestion,
)
from ghoul_quiz.errors import NotFoundError, RateLimitError

from ..exceptions import QuizBusy, QuizEmailMissing, QuizModeDisabled, QuizSessionMissing

logger = logging.getLogger(__name__)

DEFAULT_RETRY_AFTER = 60

Result = TypeVar("Result")


class QuizService:
    def __init__(self, email: str | None, base_url: str = DEFAULT_BASE_URL) -> None:
        self._email = email
        self._api = GhoulQuizAPI(base_url=base_url)

    def _ensure_session(self) -> None:
        # Проверяется на каждом вызове: после нового входа через ghoul-quiz-register сессия
        # подхватится без перезапуска.
        if self._api.tokens is not None:
            return
        if not self._email:
            raise QuizEmailMissing()
        if not self._api.load_saved_token(self._email):
            raise QuizSessionMissing(self._email)

    async def _call(self, request: Callable[[], Awaitable[Result]]) -> Result:
        self._ensure_session()
        try:
            return await request()
        except RateLimitError as exc:
            raise self._busy(exc) from exc

    async def _call_optional_mode(self, request: Callable[[], Awaitable[Result]]) -> Result:
        # Сервер может не включать режим: тогда на вопрос он отвечает 404.
        try:
            return await self._call(request)
        except NotFoundError as exc:
            raise QuizModeDisabled() from exc

    async def get_random_quiz(self) -> Question:
        return await self._call(self._api.get_random_question)

    async def get_answer_by_id(self, question_id: int) -> Answer:
        return await self._call(lambda: self._api.get_answer(question_id=question_id))

    async def get_random_whois(self) -> WhoisQuestion:
        return await self._call_optional_mode(self._api.get_random_whois)

    async def get_whois_answer(self, question_id: int) -> WhoisAnswer:
        return await self._call(lambda: self._api.get_whois_answer(question_id))

    async def get_random_true_false(self) -> TrueFalseQuestion:
        return await self._call_optional_mode(self._api.get_random_true_false)

    async def get_true_false_answer(self, question_id: int) -> TrueFalseAnswer:
        return await self._call(lambda: self._api.get_true_false_answer(question_id))

    def _busy(self, exc: RateLimitError) -> QuizBusy:
        # У API два лимита с одним текстом ошибки (на IP в минуту и на аккаунт в час):
        # какой сработал, видно только по заголовку политики.
        logger.warning("Квиз ответил 429, политика: %s", exc.headers.get("RateLimit-Policy"))
        return QuizBusy(exc.retry_after or DEFAULT_RETRY_AFTER)

    async def close(self) -> None:
        await self._api.close()
