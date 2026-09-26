"""QuizService: один клиент ghoul_quiz 0.2 на процесс, сессия из TokenManager."""

import time

import pytest
from ghoul_quiz import AuthenticationRequiredError, Question, TokenManager, TokenPair

from src.bot.services.quiz import QuizService

from .test_common_routers import seed
from .test_ghoul_routers import seed_ghoul

URL = "https://quiz.test/api"
EMAIL = "bot@example.com"


@pytest.fixture(autouse=True)
def token_file(tmp_path, monkeypatch):
    path = tmp_path / "tokens.json"
    monkeypatch.setenv("GHOUL_QUIZ_TOKEN_PATH", str(path))
    return path


def save_session(email: str = EMAIL, api_url: str = URL) -> None:
    now = time.time()
    tokens = TokenPair(
        access_token="eyJ.test.access",
        refresh_token="refresh-test",
        expires_at=now + 900,
        refresh_expires_at=now + 30 * 86400,
    )
    TokenManager.save_session(email, tokens, api_url=api_url)


class Asked:
    """Подмена сетевого запроса: сессия проверяется до него, вопрос не нужен."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> Question:
        self.calls += 1
        return Question(id=1, question="Кто?", answer_options=["a", "b", "c", "d"], answer_group="g")


@pytest.fixture
async def service():
    quiz = QuizService(email=EMAIL, base_url=URL)
    yield quiz
    await quiz.close()


async def test_without_email_fails_before_any_request():
    quiz = QuizService(email=None, base_url=URL)
    asked = Asked()
    quiz._api.get_random_question = asked  # type: ignore[method-assign]

    with pytest.raises(AuthenticationRequiredError, match="GHOUL_QUIZ_EMAIL"):
        await quiz.get_random_quiz()
    assert asked.calls == 0


async def test_without_saved_session_points_to_register(service):
    with pytest.raises(AuthenticationRequiredError, match="ghoul-quiz-register"):
        await service.get_answer_by_id(1)


async def test_session_saved_for_another_server_is_ignored(service):
    save_session(api_url="https://other.test/api")

    with pytest.raises(AuthenticationRequiredError):
        await service.get_random_quiz()


async def test_loads_saved_session_and_asks(service):
    save_session()
    service._api.get_random_question = Asked()  # type: ignore[method-assign]

    question = await service.get_random_quiz()

    assert question.id == 1
    assert service._api.tokens is not None
    assert service._api.tokens.refresh_token == "refresh-test"


async def test_picks_up_new_login_after_session_was_dropped(service):
    save_session()
    asked = Asked()
    service._api.get_random_question = asked  # type: ignore[method-assign]
    await service.get_random_quiz()

    # Так библиотека сбрасывает сессию, когда refresh-токен истёк.
    service._api.clear()
    TokenManager.delete(EMAIL)
    with pytest.raises(AuthenticationRequiredError):
        await service.get_random_quiz()

    save_session()  # новый вход через ghoul-quiz-register
    await service.get_random_quiz()
    assert asked.calls == 2


async def test_quiz_without_session_answers_global_error(
    dispatcher, send, session_factory, monkeypatch
):
    # Через настоящий create_context: /quiz берёт клиент диспетчера.
    monkeypatch.setattr(dispatcher, "quiz_service", QuizService(email=None, base_url=URL))
    await seed(session_factory, 700001)
    await seed_ghoul(session_factory, 700001)

    (reply,) = await send("/quiz", uid=700001)

    assert "GHOUL_QUIZ_EMAIL" in reply
    (error,) = dispatcher.errors
    assert isinstance(error, AuthenticationRequiredError)
    dispatcher.errors.clear()  # ошибка ожидаемая
