from datetime import datetime

from sqlalchemy import BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    media_type: Mapped[str] = mapped_column(nullable=False)

    telegram_file_id: Mapped[str] = mapped_column(nullable=True)

    # file_id одного файла в разных сообщениях бывает разным, file_unique_id постоянен:
    # по нему /remove_gif находит гифку из ответа.
    file_unique_id: Mapped[str | None] = mapped_column(nullable=True, index=True)

    collection: Mapped[str] = mapped_column(nullable=False)

    path: Mapped[str] = mapped_column(nullable=False)

    uploaded_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
