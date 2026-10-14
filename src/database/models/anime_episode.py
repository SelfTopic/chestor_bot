from datetime import datetime

from sqlalchemy import BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AnimeEpisode(Base):
    __tablename__ = "anime_episodes"

    season: Mapped[int] = mapped_column(primary_key=True)
    episode: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    added_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
