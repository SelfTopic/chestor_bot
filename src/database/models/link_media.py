from datetime import datetime
from typing import Optional

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LinkMediaCache(Base):
    __tablename__ = "link_media_cache"

    key: Mapped[str] = mapped_column(primary_key=True)
    video_file_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    photo_file_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    audio_file_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
