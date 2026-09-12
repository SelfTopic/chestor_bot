from typing import Any, Optional

from src.database.models import DuelSession

from ..repositories import DuelSessionRepository


class DuelService:
    """Тонкая обёртка над `DuelSessionRepository` для DI - роутер по
    конвенции проекта вызывает только сервисы, не репозитории напрямую
    (см. `BattleRecordService`/`BattleService` для того же паттерна)."""

    def __init__(self, duel_session_repository: DuelSessionRepository) -> None:
        self.duel_session_repository = duel_session_repository

    async def create(
        self,
        chat_id: int,
        initiator_telegram_id: int,
        target_telegram_id: int,
        is_private_origin: bool = False,
    ) -> DuelSession:
        return await self.duel_session_repository.create(
            chat_id=chat_id,
            initiator_telegram_id=initiator_telegram_id,
            target_telegram_id=target_telegram_id,
            is_private_origin=is_private_origin,
        )

    async def atomic_update(
        self, duel_id: int, expected_stage: str, **fields: Any
    ) -> Optional[DuelSession]:
        return await self.duel_session_repository.atomic_update(
            duel_id, expected_stage, **fields
        )

    async def get(self, duel_id: int) -> Optional[DuelSession]:
        return await self.duel_session_repository.get(duel_id)

    async def find_active_for(self, telegram_id: int) -> Optional[DuelSession]:
        return await self.duel_session_repository.find_active_for(telegram_id)


__all__ = ["DuelService"]
