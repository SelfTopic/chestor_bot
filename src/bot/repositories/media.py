import logging
from typing import Optional

from sqlalchemy import delete, exists, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Media
from ..exceptions import MediaNotFoundInDatabase
from ..types.insert import MediaInsert
from .base import Base

logger = logging.getLogger(__name__)


class MediaRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(self, media_insert: MediaInsert) -> Media:
        stmt = (
            insert(Media)
            .values(
                media_type=media_insert.media_type,
                telegram_file_id=media_insert.telegram_file_id,
                collection=media_insert.collection,
                path=media_insert.path,
                uploaded_by=media_insert.uploaded_by,
            )
            .returning(Media)
        )

        media = await self.session.scalar(stmt)

        if not media:
            raise MediaNotFoundInDatabase()

        return media

    async def get_by_file_id(self, file_id: int) -> Optional[Media]:
        stmt = select(Media).filter(Media.telegram_file_id == file_id)
        media = await self.session.scalar(stmt)

        return media

    async def get_by_path(self, path: str) -> Optional[Media]:
        stmt = select(Media).filter(Media.path == path)
        media = await self.session.scalar(stmt)

        return media

    async def delete_by_file_id(self, file_id: int) -> None:
        stmt = delete(Media).filter(Media.telegram_file_id == file_id)
        await self.session.execute(stmt)

    async def delete_by_path(self, path: str) -> None:
        stmt = delete(Media).filter(Media.path == path)
        await self.session.execute(stmt)

    async def exists_by_file_id(self, file_id: int) -> Optional[bool]:
        stmt = select(exists().where(Media.telegram_file_id == file_id))
        result = await self.session.scalar(stmt)

        return result

    async def exists_by_path(self, path: str) -> Optional[bool]:
        stmt = select(exists().where(Media.path == path))
        result = await self.session.scalar(stmt)

        return result

    async def update_file_id(self, path: str, new_file_id: str) -> Media:
        stmt = (
            update(Media)
            .filter(Media.path == path)
            .values({Media.telegram_file_id: new_file_id})
        ).returning(Media)
        media = await self.session.scalar(stmt)

        if not media:
            raise MediaNotFoundInDatabase()

        return media
