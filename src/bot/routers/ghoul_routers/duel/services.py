"""Пучок сервисов, нужных для проведения дуэли целиком - и в живом
хендлере (DI-инжектированные), и в фоновой таймаут-задаче (собранные
вручную от свежей сессии, см. `build_services`). Единая форма ради того,
чтобы `fight.py` не знал, из какого из двух контекстов его вызвали."""

from typing import NamedTuple

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from ....repositories import (
    ActiveBattleRepository,
    BattleRepository,
    ChatRepository,
    DeathLogRepository,
    DuelSessionRepository,
    GhoulRepository,
    ScheduledNotificationRepository,
    UserCooldownRepository,
    UserRepository,
)
from ....repositories.balances_log import BalancesLogRepository
from ....services import (
    BattleRecordService,
    BattleService,
    BattleTextGenerator,
    DialogService,
    DuelService,
    GhoulService,
    LevelUpService,
    MobService,
    UserService,
)


class Services(NamedTuple):
    user_service: UserService
    ghoul_service: GhoulService
    battle_service: BattleService
    battle_text_generator: BattleTextGenerator
    level_up_service: LevelUpService
    battle_record_service: BattleRecordService
    duel_service: DuelService


def build_services(session: AsyncSession, bot: Bot) -> Services:
    """Тот же приём, что `NotificationTicker._tick` - строит сервисы
    вручную от СВЕЖЕЙ сессии, а не переиспользует DI-контейнер. Нужно
    только фоновым таймаут-задачам: `DatabaseMiddleware` коммитит и
    закрывает сессию запроса сразу после возврата из хендлера (см.
    `database_middleware.py`), поэтому к моменту срабатывания таймера
    DI-инжектированные в хендлере сервисы уже держат мёртвую сессию."""

    user_repository = UserRepository(session)
    ghoul_repository = GhoulRepository(session)
    user_cooldown_repository = UserCooldownRepository(session)
    chat_repository = ChatRepository(session)
    balances_log_repository = BalancesLogRepository(session)

    user_service = UserService(
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
        balances_log_repository,
    )
    ghoul_service = GhoulService(
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
        notification_repository=ScheduledNotificationRepository(session),
        death_log_repository=DeathLogRepository(session),
    )
    dialog_service = DialogService()
    battle_service = BattleService(mob_service=MobService())
    battle_text_generator = BattleTextGenerator(dialog_service=dialog_service)
    level_up_service = LevelUpService(
        user_service=user_service,
        ghoul_service=ghoul_service,
        dialog_service=dialog_service,
        bot=bot,
    )
    battle_record_service = BattleRecordService(
        active_battle_repository=ActiveBattleRepository(session),
        battle_repository=BattleRepository(session),
    )
    duel_service = DuelService(DuelSessionRepository(session))

    return Services(
        user_service=user_service,
        ghoul_service=ghoul_service,
        battle_service=battle_service,
        battle_text_generator=battle_text_generator,
        level_up_service=level_up_service,
        battle_record_service=battle_record_service,
        duel_service=duel_service,
    )


__all__ = ["Services", "build_services"]
