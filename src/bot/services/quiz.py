"""
Квиз по «Токийскому гулю» через ghoul_quiz 0.2 — один клиент на процесс.

С 0.2 сервер выдаёт пару access/refresh, и refresh одноразовый. Прод создаёт
GhoulQuizAPI заново на каждый апдейт с постоянным GHOUL_QUIZ_API_KEY; с 0.2 так
нельзя: каждый экземпляр сам обновлял бы пару и сжигал бы refresh-токен
остальных. Поэтому клиент один: его создаёт Dispatcher, закрывает on_shutdown,
а ctx.ghoul_quiz_service отдаёт его всем апдейтам.

Сессия — из хранилища ghoul_quiz (TokenManager) по GHOUL_QUIZ_EMAIL. Файл
хранилища — GHOUL_QUIZ_TOKEN_PATH, иначе ./.ghoul_quiz/tokens.json (в корне
проекта, в git и в образ не попадает). Войти один раз: `ghoul-quiz-register`.
Refresh-токены библиотека сама пишет обратно в этот файл. Одну сессию нельзя
держать в двух местах сразу (например, локально и в облаке): первое же
обновление сожжёт refresh-токен у второго — каждому окружению нужен свой вход.

Сессия загружается при первом вопросе, а не при старте: без неё бот работает,
а /quiz отвечает global_error, как у прода при любой ошибке API.
"""

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
        # Проверяется при каждом вызове, а не один раз: если сессия истекла и
        # библиотека её сбросила, после нового входа через ghoul-quiz-register
        # бот подхватит её без перезапуска.
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
