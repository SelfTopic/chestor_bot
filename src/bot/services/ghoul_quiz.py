from ghoul_quiz import GhoulQuizAPI

from ...config import settings


class GhoulQuizService:
    def __init__(self):
        self.ghoul_quiz_api = GhoulQuizAPI(
            api_key=settings.GHOUL_QUIZ_API_KEY.get_secret_value()
        )

    async def get_random_quiz(self):
        return await self.ghoul_quiz_api.get_random_question()

    async def get_answer_by_id(self, question_id: int):
        return await self.ghoul_quiz_api.get_answer(question_id=question_id)

    async def get_answer_by_question(self, question: str):
        return await self.ghoul_quiz_api.get_answer(question_text=question)


__all__ = ["GhoulQuizService"]
