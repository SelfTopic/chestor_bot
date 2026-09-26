"""Пользователи пачкой — там, где прод берёт их по одному в цикле (топы)."""

from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User


class UserNameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def first_names(self, telegram_ids: Collection[int]) -> dict[int, str]:
        """Имя каждого из telegram_ids одним запросом; кого нет в users — нет в ответе."""
        if not telegram_ids:
            return {}
        rows = await self.session.execute(
            select(User.telegram_id, User.first_name).where(User.telegram_id.in_(telegram_ids))
        )
        return {telegram_id: first_name for telegram_id, first_name in rows.tuples()}
