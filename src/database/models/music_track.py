from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MusicTrack(Base):
    __tablename__ = "music_tracks"

    track_id: Mapped[str] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
