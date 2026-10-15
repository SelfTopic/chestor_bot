from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    name: Mapped[Optional[str]] = mapped_column(nullable=True)

    balance: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    dissolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class FamilyMember(Base):
    __tablename__ = "family_members"

    # Ключ — сам игрок: состоять можно только в одной семье.
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), primary_key=True
    )

    family_id: Mapped[int] = mapped_column(
        ForeignKey(Family.id, ondelete="CASCADE"), nullable=False, index=True
    )

    joined_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class MarriageProposal(Base):
    __tablename__ = "marriage_proposals"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    proposer_telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )
    target_telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )

    family_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(Family.id, ondelete="CASCADE"), nullable=True
    )

    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    stage: Mapped[str] = mapped_column(nullable=False, default="awaiting", index=True)

    declined_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class MarriageConsent(Base):
    __tablename__ = "marriage_consents"

    proposal_id: Mapped[int] = mapped_column(
        ForeignKey(MarriageProposal.id, ondelete="CASCADE"), primary_key=True
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class FamilyRename(Base):
    __tablename__ = "family_renames"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    family_id: Mapped[int] = mapped_column(
        ForeignKey(Family.id, ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(nullable=False)
    proposer_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    consented: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False)

    stage: Mapped[str] = mapped_column(nullable=False, default="awaiting", index=True)
    declined_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
