from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .chat import Chat
from .user import User


class ChatParticipant(Base):
    """"Кто вообще писал в этом чате" - самый дешёвый доступный сигнал о
    членстве (Bot API не даёт список участников чата целиком ни одним
    методом, только косвенно через события/апдейты) - апсертится в
    SyncEntitiesService.sync на каждое сообщение в группе, используется
    командой "выбери участника" (fun_router.py). Не претендует на полноту
    (тихие участники, ни разу не написавшие, сюда не попадут) - для
    развлекательной команды этого достаточно."""

    __tablename__ = "chat_participants"

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Chat.telegram_id, ondelete="CASCADE"),
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        primary_key=True,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
