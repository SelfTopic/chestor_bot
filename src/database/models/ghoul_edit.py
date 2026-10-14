from datetime import datetime

from sqlalchemy import BigInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class GhoulEdit(Base):
    __tablename__ = "ghoul_edits"
    __table_args__ = (UniqueConstraint("channel_id", "channel_message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(nullable=False)
    file_unique_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    added_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
