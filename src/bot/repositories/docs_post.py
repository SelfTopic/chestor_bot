from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import DocsPost
from .base import Base


@dataclass(frozen=True)
class PublishedPost:
    message_id: int
    digest: str


class DocsPostRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def published(self, channel: str) -> dict[str, PublishedPost]:
        rows = await self.session.scalars(select(DocsPost).where(DocsPost.channel == channel))
        return {row.slug: PublishedPost(row.message_id, row.digest) for row in rows}

    async def save(self, channel: str, slug: str, post: PublishedPost) -> None:
        values = {"message_id": post.message_id, "digest": post.digest}
        stmt = insert(DocsPost).values(channel=channel, slug=slug, **values)
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[DocsPost.channel, DocsPost.slug], set_=values
            )
        )

    async def forget(self, channel: str, slug: str) -> None:
        await self.session.execute(
            delete(DocsPost).where(DocsPost.channel == channel, DocsPost.slug == slug)
        )
