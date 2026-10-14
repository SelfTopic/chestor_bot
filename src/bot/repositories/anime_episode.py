from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import AnimeEpisode
from .base import Base


class AnimeEpisodeRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(
        self, season: int, episode: int, file_id: str, channel_id: int, channel_message_id: int
    ) -> None:
        values = dict(
            file_id=file_id, channel_id=channel_id, channel_message_id=channel_message_id
        )
        stmt = insert(AnimeEpisode).values(season=season, episode=episode, **values)
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[AnimeEpisode.season, AnimeEpisode.episode], set_=values
            )
        )

    async def file_id(self, season: int, episode: int) -> str | None:
        stmt = select(AnimeEpisode.file_id).where(
            AnimeEpisode.season == season, AnimeEpisode.episode == episode
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def last_posts(self) -> dict[int, int]:
        stmt = select(
            AnimeEpisode.channel_id, func.max(AnimeEpisode.channel_message_id)
        ).group_by(AnimeEpisode.channel_id)
        return {channel: post for channel, post in (await self.session.execute(stmt)).all()}
