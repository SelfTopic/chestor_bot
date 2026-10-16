from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PromoCode(Base):
    __tablename__ = "promo_codes"
    # Название уникально только среди живых кодов: удалённый остаётся в истории.
    __table_args__ = (
        Index(
            "uq_promo_codes_live_name",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    rewards: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    activations_limit: Mapped[int] = mapped_column(nullable=False)
    activations_used: Mapped[int] = mapped_column(nullable=False, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class PromoActivation(Base):
    __tablename__ = "promo_activations"

    promo_id: Mapped[int] = mapped_column(
        ForeignKey(PromoCode.id, ondelete="CASCADE"), primary_key=True
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
