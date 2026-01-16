from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .cooldown import Cooldown
from .user import User


class UserCooldown(Base):
    __tablename__ = "users_cooldowns"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            User.telegram_id, 
            ondelete="CASCADE"
        ),
        primary_key=True
    )

    cooldown_id: Mapped[int] = mapped_column(
        ForeignKey(
            Cooldown.id,
            ondelete="CASCADE"
        ),
        primary_key=True
    )

    end_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False    
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now()    
    )
