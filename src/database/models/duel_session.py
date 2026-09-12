from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class DuelSession(Base):
    """"Разговорное" состояние одной дуэли между роутером и Telegram - кто
    кого позвал, в каком чате, на какой стадии, что уже решено. Отдельно
    от `ActiveBattle` (эфемерный лок "занят прямо сейчас" - живёт весь
    жизненный цикл дуэли, но ничего не знает про чат/стадии/кнопки) и от
    `Battle` (постоянная история - пишется только когда исход уже
    известен целиком).

    `stage` - строка (не Enum, см. конвенцию `ActiveBattle.status`):
    "awaiting_consent" -> "awaiting_serious_or_handicap" (пропускается при
    перевесе < power_ratio_threshold) -> "running" (короткоживущая метка
    "бой уже разыгрывается") -> "awaiting_winner_choice" (пропускается при
    настоящей ничьей) -> "done".

    Переходы между стадиями идут ТОЛЬКО через `DuelSessionRepository.
    atomic_update` (UPDATE ... WHERE id=X AND stage=expected RETURNING) -
    это единственное, что защищает от гонки "нажатие кнопки против
    сработавшего таймаута" без блокировок в коде (см. чат)."""

    __tablename__ = "duel_sessions"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    # Чат, где вызвана дуэль - туда же едут согласие/лог боя/выбор
    # победителя (решено в чате: "чтобы все участники видели
    # происходящее"). Может быть и группой, и ЛС инициатора с ботом.
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # ВАЖНО: если дуэль вызвана из ЛС инициатора с ботом (например,
    # соперник указан через @username без общего группового чата) -
    # `chat_id` бесполезен для "чтобы все видели": это приватный чат
    # ровно между инициатором и ботом, соперник в нём физически не
    # состоит и никогда не увидит там ни кнопки, ни лог боя (найдено как
    # баг при ревью - Telegram ЛС не бывает "на троих"). В этом случае
    # invite_router/fight.py дублируют отправку в ОБА личных чата
    # (initiator_telegram_id и target_telegram_id) вместо одного chat_id.
    is_private_origin: Mapped[bool] = mapped_column(nullable=False, default=False)

    initiator_telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )
    target_telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )

    stage: Mapped[str] = mapped_column(nullable=False, default="awaiting_consent")

    initiator_consented: Mapped[bool] = mapped_column(nullable=False, default=False)
    target_consented: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Кому решать "всерьёз/фора" (1.5) - всегда более сильная сторона по
    # power_ratio, заполняется только если этот шаг вообще наступил.
    favored_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    compress_hp: Mapped[Optional[bool]] = mapped_column(nullable=True)

    consent_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    outcome_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    winner_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    loser_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    winner_choice: Mapped[Optional[str]] = mapped_column(nullable=True)  # "rob"|"release"|"eat"

    # BattleResult.ended_naturally - запоминается здесь для того же
    # "battles - append-only, пишем один раз" резона, что и
    # reward_level_progress: сама запись в battles откладывается до шага
    # выбора победителя (или его таймаута), а к тому моменту исходный
    # BattleResult уже не под рукой.
    ended_naturally: Mapped[Optional[bool]] = mapped_column(nullable=True)

    # level_progress, начисленный победителю сразу после боя - запоминается
    # здесь, чтобы шаг 5 (выбор исхода) мог честно записать его в `battles`
    # вместе с остальными наградами (battles - append-only, пишется одним
    # разом только когда исход уже известен целиком).
    reward_level_progress: Mapped[Optional[float]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
