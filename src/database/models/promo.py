from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    rewards: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    activations_limit: Mapped[int] = mapped_column(nullable=False)
    activations_used: Mapped[int] = mapped_column(nullable=False, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class PromoActivation(Base):
    __tablename__ = "promo_activations"

    promo_id: Mapped[int] = mapped_column(
        ForeignKey(PromoCode.id, ondelete="CASCADE"), primary_key=True
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
