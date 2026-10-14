from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import LinkMediaCache
from ..types import CachedMedia, CachedSlideshow, CachedVideo
from .base import Base


class LinkMediaRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> CachedMedia | None:
        row = await self.session.get(LinkMediaCache, key)
        if row is None:
            return None
        if row.video_file_id is not None:
            return CachedVideo(row.video_file_id)
        if row.photo_file_ids:
            return CachedSlideshow(tuple(row.photo_file_ids), row.audio_file_id)
        return None

    async def save(self, key: str, media: CachedMedia) -> None:
        if isinstance(media, CachedVideo):
            values = dict(video_file_id=media.file_id, photo_file_ids=[], audio_file_id=None)
        else:
            values = dict(
                video_file_id=None,
                photo_file_ids=list(media.photo_file_ids),
                audio_file_id=media.audio_file_id,
            )
        stmt = insert(LinkMediaCache).values(key=key, **values)
        await self.session.execute(
            stmt.on_conflict_do_update(index_elements=[LinkMediaCache.key], set_=values)
        )

    async def delete(self, key: str) -> None:
        await self.session.execute(delete(LinkMediaCache).where(LinkMediaCache.key == key))
