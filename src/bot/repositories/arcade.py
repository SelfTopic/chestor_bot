from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ArcadeVideo
from .base import Base


class ArcadeVideoRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def file_id(self, key: str) -> str | None:
        return await self.session.scalar(select(ArcadeVideo.file_id).where(ArcadeVideo.key == key))

    async def save(self, key: str, file_id: str) -> None:
        stmt = insert(ArcadeVideo).values(key=key, file_id=file_id)
        await self.session.execute(
            stmt.on_conflict_do_update(index_elements=[ArcadeVideo.key], set_={"file_id": file_id})
        )

    async def forget(self, key: str) -> None:
        await self.session.execute(delete(ArcadeVideo).where(ArcadeVideo.key == key))
