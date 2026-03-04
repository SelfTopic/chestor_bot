from datetime import datetime

from sqlalchemy import BigInteger, UniqueConstraint, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.bot.types.rp_commands import TypeRpCommandEnum

from .base import Base


class Rp(Base):
    __tablename__ = "rp_commands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    command: Mapped[str] = mapped_column(nullable=False, index=True)

    action: Mapped[str] = mapped_column(nullable=False)

    type_command: Mapped[TypeRpCommandEnum] = mapped_column(
        SqlEnum(TypeRpCommandEnum), nullable=False
    )

    file_id: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("chat_id", "command", name="unique_chat_command"),
    )

    def to_kwargs(self):
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "command": self.command,
            "action": self.action,
            "type_command": self.type_command,
            "file_id": self.file_id,
            "created_at": self.created_at,
        }
