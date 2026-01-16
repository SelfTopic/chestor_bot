from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Media(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # TODO - дописать колонки для медиа
