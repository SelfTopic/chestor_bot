from ghoul_quiz import DEFAULT_BASE_URL, Answer, GhoulQuizAPI, Question

from ..exceptions import QuizEmailMissing, QuizSessionMissing


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

    async def get_random_quiz(self) -> Question:
        self._ensure_session()
        return await self._api.get_random_question()

    async def get_answer_by_id(self, question_id: int) -> Answer:
        self._ensure_session()
        return await self._api.get_answer(question_id=question_id)

    async def close(self) -> None:
        await self._api.close()
