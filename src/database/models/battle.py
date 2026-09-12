from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class Battle(Base):
    """Постоянная история завершённых боёв (BATTLE_ENGINE.md 5.1) - и
    дуэлей, и боёв с мобами в одной таблице. `participant_b_telegram_id`
    (дуэль) и `mob_name` (бой с мобом) взаимоисключающие по смыслу - у
    моба нет строки `User`, поэтому вместо телеграм-id только имя для
    истории. `winner` - "a"/"b"/None, та же схема, что уже несёт
    `BattleResult.winner` в самом движке (не выдумываем новую).

    `is_forced`/`winner_choice`/`reward_*` описывают механики, которых в
    коде ЕЩЁ НЕТ (засада моба "3b" при еде, ЛС-выбор победителя
    "ограбить/отпустить/съесть" - см. BATTLE_DESIGN.md "Исход боя") -
    колонки заводятся заранее, тем же приёмом, что `Ghoul.is_dead`/
    `deaths` были заведены до самого боевого движка."""

    __tablename__ = "battles"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    battle_type: Mapped[str] = mapped_column(nullable=False)  # "mob" | "duel"

    participant_a_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=False,
    )

    participant_b_telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=True,
    )

    mob_name: Mapped[Optional[str]] = mapped_column(nullable=True)

    winner: Mapped[Optional[str]] = mapped_column(nullable=True)  # "a" | "b" | None (ничья)
    ended_naturally: Mapped[bool] = mapped_column(nullable=False)

    # Причина боя - принуждённый (например, будущая засада моба во время
    # еды, "3b") или добровольный (сам вызвал "бить моба" / оба согласились
    # на дуэль). Пока всегда False - ни одной формы принуждённого боя ещё
    # не существует.
    is_forced: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Что выбрал победитель после боя - "rob" | "release" | "eat" (см.
    # BATTLE_DESIGN.md "Исход боя"). Имеет смысл только для дуэли с явным
    # победителем - для боя с мобом или ничьи всегда None (выбирать не из
    # чего). Сама механика выбора (ЛС + таймер 1 минута → авто "release")
    # ещё не реализована.
    winner_choice: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Сколько и чего заработал победитель - раздельные колонки по видам
    # награды (не единая пара тип+сумма), потому что за один бой может
    # начислиться сразу НЕСКОЛЬКО видов одновременно (базовый
    # level_progress за победу всегда + RC, если выбрано "eat").
    reward_level_progress: Mapped[Optional[float]] = mapped_column(nullable=True)
    reward_rc: Mapped[Optional[int]] = mapped_column(nullable=True)
    reward_balance: Mapped[Optional[int]] = mapped_column(nullable=True)  # "rob" - % баланса

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
