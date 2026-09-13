from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .chat import Chat
from .user import User


class ChatParticipant(Base):
    """"Кто вообще в этом чате" - самый дешёвый доступный сигнал о членстве
    (Bot API не даёт список участников чата целиком ни одним методом,
    только косвенно через события/апдейты). Две колонки данных с разной
    природой:

    - `joined_at`/`join_method` - пишутся ОДИН раз событием входа
      (`chat_member_update_routers/new_chat_member.py`, `ChatMemberUpdated`)
      - NULL, если участник уже был в чате до появления этой фичи (для
      уже вошедших используется только счётчик сообщений, см.
      `SyncEntitiesService.sync`).
    - `messages_*`/`last_seen_at` - обновляются на КАЖДОЕ сообщение
      (`ChatParticipantRepository.record_message`) - календарные окна
      (сегодня/неделя/месяц) считаются лениво, сравнением `last_seen_at`
      с текущим моментом в самом UPDATE (тот же приём лени, что и у
      голода/регена - никакого фонового сброса по расписанию не нужно).

    При выходе из чата (`left_chat_member.py`) строка целиком удаляется -
    "регистрация И удаление", как попросил автор; повторный вход - чистый
    лист (новый `joined_at`, счётчики с нуля)."""

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

    messages_total: Mapped[int] = mapped_column(nullable=False, default=0)
    messages_today: Mapped[int] = mapped_column(nullable=False, default=0)
    messages_week: Mapped[int] = mapped_column(nullable=False, default=0)
    messages_month: Mapped[int] = mapped_column(nullable=False, default=0)

    joined_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # "self" | "invite_link" | "join_request" | "chat_folder_invite_link" |
    # "added_by_admin" - см. ChatMemberJoinMethod в chat_member_update_routers.
    join_method: Mapped[Optional[str]] = mapped_column(nullable=True)
