from ghoul_quiz import (
    DEFAULT_BASE_URL,
    Answer,
    AuthenticationRequiredError,
    GhoulQuizAPI,
    Question,
)


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
            raise AuthenticationRequiredError("Квиз: не задан GHOUL_QUIZ_EMAIL")
        if not self._api.load_saved_token(self._email):
            raise AuthenticationRequiredError(
                f"Квиз: нет сохранённой сессии для {self._email}, "
                "войди через ghoul-quiz-register"
            )

    async def get_random_quiz(self) -> Question:
        self._ensure_session()
        return await self._api.get_random_question()

    async def get_answer_by_id(self, question_id: int) -> Answer:
        self._ensure_session()
        return await self._api.get_answer(question_id=question_id)

    async def close(self) -> None:
        await self._api.close()
