from datetime import timedelta

from ..repositories.quiz_streak import ExpiredStreak, HeldStreak, QuizStreakRepository


class QuizStreakService:
    def __init__(self, repository: QuizStreakRepository, lifetime: timedelta) -> None:
        self._repository = repository
        self._lifetime = lifetime

    async def hold(
        self,
        telegram_id: int,
        chat_id: int,
        message_id: int,
        rich: str,
        streak: int,
    ) -> None:
        await self._repository.hold(
            telegram_id, chat_id, message_id, rich, streak, self._lifetime
        )

    async def take(self, telegram_id: int, message_id: int) -> HeldStreak | None:
        return await self._repository.take(telegram_id, message_id)

    async def take_expired(self) -> list[ExpiredStreak]:
        return await self._repository.take_expired()
