from datetime import datetime

from sqlalchemy import BigInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DocsPost(Base):
    __tablename__ = "docs_posts"

    channel: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
