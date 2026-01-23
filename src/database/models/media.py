from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    media_type_bit: Mapped[int] = mapped_column(nullable=False)

    telegram_file_id: Mapped[str] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
