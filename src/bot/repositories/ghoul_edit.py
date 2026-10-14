from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import GhoulEdit
from .base import Base


class GhoulEditRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self, file_id: str, file_unique_id: str, channel_id: int, channel_message_id: int
    ) -> bool:
        stmt = (
            insert(GhoulEdit)
            .values(
                file_id=file_id,
                file_unique_id=file_unique_id,
                channel_id=channel_id,
                channel_message_id=channel_message_id,
            )
            .on_conflict_do_nothing()
            .returning(GhoulEdit.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def random_file_id(self) -> str | None:
        stmt = select(GhoulEdit.file_id).order_by(func.random()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()
