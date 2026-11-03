from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


# file_id роликов автоматов: ключ — путь файла и время его изменения, так перерендеренный ролик
# не получит file_id прежнего.
class ArcadeVideo(Base):
    __tablename__ = "arcade_videos"

    key: Mapped[str] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
