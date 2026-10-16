from collections.abc import Collection
from contextvars import ContextVar
from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from .repositories import (
    ActiveBattleRepository,
    AnimeEpisodeRepository,
    BalancesLogRepository,
    BattleRepository,
    ChatParticipantRepository,
    ChatRepository,
    DeathLogRepository,
    DuelSessionRepository,
    FamilyRepository,
    GhoulEditRepository,
    GhoulRepository,
    LotteryRepository,
    MediaRepository,
    PromoRepository,
    ModerationRepository,
    RpCommandsRepository,
    ScheduledNotificationRepository,
    TransferRepository,
    UserCooldownRepository,
    UserRepository,
    WalletRepository,
)
from .repositories.fight import FightRepository
from .repositories.user_names import UserNameRepository
from .services import (
    BanService,
    BattleEngine,
    BattleRecordService,
    ChatService,
    CooldownService,
    DuelService,
    GhoulService,
    MediaService,
    MobService,
    PlayerLookupService,
    ResetService,
    StatsEditService,
    TransferService,
    UserService,
)
from .services.battle import BattleService
from .services.broadcast import BroadcastService
from .services.dialog import DialogService
from .services.family import FamilyService
from .services.ghoul_game import CoffeeService, LotteryService
from .services.level_up import LevelUpService
from .services.moderation import ModerationService
from .services.notify import Notifier
from .services.promo import PromoService
from .services.stat_upgrade import StatUpgradeService

# Сессия БД текущей работы: в апдейте её ставит DatabaseMiddleware, вне апдейта (тикер
# дуэлей) — тот, кто работает. Процессные сервисы вроде RpCommandsService берут её отсюда.
session_context: ContextVar[AsyncSession] = ContextVar("session_context")


def current_session() -> AsyncSession:
    return session_context.get()


def rp_commands_repository() -> RpCommandsRepository:
    return RpCommandsRepository(current_session())


# Репозитории и сервисы на текущей сессии, каждый — один раз на объект. AppContext — это
# SessionServices апдейта; вне апдейта объект создаётся сам.
class SessionServices:
    dialog_service: DialogService
    mob_service: MobService

    def __init__(
        self, dialog_service: DialogService, notifier: Notifier, mob_service: MobService
    ) -> None:
        self.dialog_service = dialog_service
        self._notifier = notifier
        self.mob_service = mob_service

    @cached_property
    def notifier(self) -> Notifier:
        return self._notifier

    @property
    def session(self) -> AsyncSession:
        return current_session()

    @cached_property
    def user_repository(self) -> UserRepository:
        return UserRepository(self.session)

    @cached_property
    def ghoul_repository(self) -> GhoulRepository:
        return GhoulRepository(self.session)

    @cached_property
    def user_cooldown_repository(self) -> UserCooldownRepository:
        return UserCooldownRepository(self.session)

    @cached_property
    def chat_repository(self) -> ChatRepository:
        return ChatRepository(self.session)

    @cached_property
    def chat_participant_repository(self) -> ChatParticipantRepository:
        return ChatParticipantRepository(self.session)

    @cached_property
    def media_repository(self) -> MediaRepository:
        return MediaRepository(self.session)

    @cached_property
    def ghoul_edit_repository(self) -> GhoulEditRepository:
        return GhoulEditRepository(self.session)

    @cached_property
    def anime_episode_repository(self) -> AnimeEpisodeRepository:
        return AnimeEpisodeRepository(self.session)

    @cached_property
    def moderation_repository(self) -> ModerationRepository:
        return ModerationRepository(self.session)

    @cached_property
    def lottery_repository(self) -> LotteryRepository:
        return LotteryRepository(self.session)

    @cached_property
    def balances_log_repository(self) -> BalancesLogRepository:
        return BalancesLogRepository(self.session)

    @cached_property
    def transfer_repository(self) -> TransferRepository:
        return TransferRepository(self.session)

    @cached_property
    def scheduled_notification_repository(self) -> ScheduledNotificationRepository:
        return ScheduledNotificationRepository(self.session)

    @cached_property
    def death_log_repository(self) -> DeathLogRepository:
        return DeathLogRepository(self.session)

    @cached_property
    def active_battle_repository(self) -> ActiveBattleRepository:
        return ActiveBattleRepository(self.session)

    @cached_property
    def battle_repository(self) -> BattleRepository:
        return BattleRepository(self.session)

    @cached_property
    def duel_session_repository(self) -> DuelSessionRepository:
        return DuelSessionRepository(self.session)

    @cached_property
    def wallet_repository(self) -> WalletRepository:
        return WalletRepository(self.session)

    @cached_property
    def family_repository(self) -> FamilyRepository:
        return FamilyRepository(self.session)

    @cached_property
    def battle_engine(self) -> BattleEngine:
        return BattleEngine(mob_service=self.mob_service)

    @cached_property
    def battle_record_service(self) -> BattleRecordService:
        return BattleRecordService(
            active_battle_repository=self.active_battle_repository,
            battle_repository=self.battle_repository,
        )

    @cached_property
    def duel_service(self) -> DuelService:
        return DuelService(duel_session_repository=self.duel_session_repository)

    @cached_property
    def media_service(self) -> MediaService:
        return MediaService(media_repository=self.media_repository)

    @cached_property
    def user_service(self) -> UserService:
        return UserService(
            self.user_repository,
            self.ghoul_repository,
            self.user_cooldown_repository,
            self.chat_repository,
            self.balances_log_repository,
            self.wallet_repository,
        )

    @cached_property
    def ghoul_service(self) -> GhoulService:
        return GhoulService(
            self.user_repository,
            self.ghoul_repository,
            self.user_cooldown_repository,
            self.chat_repository,
            notification_repository=self.scheduled_notification_repository,
            death_log_repository=self.death_log_repository,
        )

    @cached_property
    def cooldown_service(self) -> CooldownService:
        return CooldownService(
            self.user_repository,
            self.ghoul_repository,
            self.user_cooldown_repository,
            self.chat_repository,
        )

    @cached_property
    def promo_repository(self) -> PromoRepository:
        return PromoRepository(self.session)

    @cached_property
    def promo_service(self) -> PromoService:
        return PromoService(
            self.promo_repository,
            self.ghoul_service,
            self.user_service,
            self.level_up_service,
        )

    @cached_property
    def family_service(self) -> FamilyService:
        return FamilyService(self.family_repository, self.user_service)

    @cached_property
    def chat_service(self) -> ChatService:
        return ChatService(
            self.user_repository,
            self.ghoul_repository,
            self.user_cooldown_repository,
            self.chat_repository,
            self.chat_participant_repository,
        )

    @cached_property
    def coffee_service(self) -> CoffeeService:
        return CoffeeService(
            user_service=self.user_service,
            ghoul_service=self.ghoul_service,
            cooldown_service=self.cooldown_service,
        )

    @cached_property
    def lottery_service(self) -> LotteryService:
        return LotteryService(
            user_service=self.user_service,
            cooldown_service=self.cooldown_service,
            media_service=self.media_service,
            lottery_repository=self.lottery_repository,
        )

    @cached_property
    def stat_upgrade_service(self) -> StatUpgradeService:
        return StatUpgradeService(ghoul_service=self.ghoul_service, user_service=self.user_service)

    @cached_property
    def player_lookup_service(self) -> PlayerLookupService:
        return PlayerLookupService(user_repo=self.user_repository, ghoul_repo=self.ghoul_repository)

    @cached_property
    def ban_service(self) -> BanService:
        return BanService(user_repo=self.user_repository)

    @cached_property
    def stats_edit_service(self) -> StatsEditService:
        return StatsEditService(
            user_repo=self.user_repository,
            ghoul_repo=self.ghoul_repository,
            balances_log_repo=self.balances_log_repository,
            wallet_repo=self.wallet_repository,
        )

    @cached_property
    def reset_service(self) -> ResetService:
        return ResetService(user_repo=self.user_repository, ghoul_repo=self.ghoul_repository)

    @cached_property
    def moderation_service(self) -> ModerationService:
        return ModerationService(moderation_repository=self.moderation_repository)

    @cached_property
    def transfer_service(self) -> TransferService:
        return TransferService(
            user_repository=self.user_repository,
            transfer_repository=self.transfer_repository,
            balances_log_repository=self.balances_log_repository,
            wallet_repository=self.wallet_repository,
            family_repository=self.family_repository,
        )

    @cached_property
    def level_up_service(self) -> LevelUpService:
        return LevelUpService(
            self.user_service, self.ghoul_service, self.dialog_service, self.notifier
        )

    @cached_property
    def battle_service(self) -> BattleService:
        return BattleService(
            engine=self.battle_engine,
            fights=FightRepository(self.session, self.ghoul_repository),
            ghoul_service=self.ghoul_service,
            user_service=self.user_service,
            level_up_service=self.level_up_service,
            battle_record_service=self.battle_record_service,
            duel_service=self.duel_service,
            families=self.family_repository,
        )

    @cached_property
    def broadcast_service(self) -> BroadcastService:
        return BroadcastService(self.user_repository, self.chat_repository, self.notifier)

    async def first_names(self, telegram_ids: Collection[int]) -> dict[int, str]:
        return await UserNameRepository(self.session).first_names(telegram_ids)


__all__ = ["SessionServices", "current_session", "rp_commands_repository", "session_context"]
