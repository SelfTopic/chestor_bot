from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import MusicTrack
from .base import Base


class MusicTrackRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def file_id(self, track_id: str) -> str | None:
        stmt = select(MusicTrack.file_id).where(MusicTrack.track_id == track_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def save(self, track_id: str, file_id: str) -> None:
        stmt = insert(MusicTrack).values(track_id=track_id, file_id=file_id)
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[MusicTrack.track_id], set_={"file_id": file_id}
            )
        )

    async def delete(self, track_id: str) -> None:
        await self.session.execute(delete(MusicTrack).where(MusicTrack.track_id == track_id))
