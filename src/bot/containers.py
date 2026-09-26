from contextvars import ContextVar

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from .repositories import (
    ActiveBattleRepository,
    BalancesLogRepository,
    BattleRepository,
    ChatRepository,
    DeathLogRepository,
    DuelSessionRepository,
    GhoulRepository,
    LotteryRepository,
    MediaRepository,
    RpCommandsRepository,
    ScheduledNotificationRepository,
    TransferRepository,
    UserCooldownRepository,
    UserRepository,
)
from .services import (
    BanService,
    BattleRecordService,
    BattleEngine,
    ChatService,
    CooldownService,
    DialogService,
    DuelService,
    GhoulService,
    MediaService,
    MobService,
    PlayerLookupService,
    ResetService,
    RpCommandsService,
    StatsEditService,
    TransferService,
    UserService,
    WikipediaService,
    WordleService,
)
from .services.ghoul_game import CoffeeService, LotteryService
from .services.stat_upgrade import StatUpgradeService
from .services.video import VideoCutterService, VideoWorker

session_context: ContextVar[AsyncSession] = ContextVar("session_context")


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    db_session = providers.Factory(lambda: session_context.get())

    user_repository = providers.Factory(UserRepository, session=db_session)
    ghoul_repository = providers.Factory(GhoulRepository, session=db_session)

    user_cooldown_repository = providers.Factory(
        UserCooldownRepository, session=db_session
    )
    chat_repository = providers.Factory(ChatRepository, session=db_session)

    media_repository = providers.Factory(MediaRepository, session=db_session)

    lottery_repository = providers.Factory(LotteryRepository, session=db_session)

    balances_log_repository = providers.Factory(
        BalancesLogRepository, session=db_session
    )

    transfer_repository = providers.Factory(TransferRepository, session=db_session)

    scheduled_notification_repository = providers.Factory(
        ScheduledNotificationRepository, session=db_session
    )

    death_log_repository = providers.Factory(DeathLogRepository, session=db_session)

    active_battle_repository = providers.Factory(ActiveBattleRepository, session=db_session)
    battle_repository = providers.Factory(BattleRepository, session=db_session)
    duel_session_repository = providers.Factory(DuelSessionRepository, session=db_session)

    dialog_service = providers.Factory(DialogService)

    mob_service = providers.Factory(MobService)

    battle_engine = providers.Factory(BattleEngine, mob_service=mob_service)

    battle_record_service = providers.Factory(
        BattleRecordService,
        active_battle_repository=active_battle_repository,
        battle_repository=battle_repository,
    )

    duel_service = providers.Factory(
        DuelService, duel_session_repository=duel_session_repository
    )

    media_service = providers.Factory(
        MediaService, media_repository=media_repository
    )

    user_service = providers.Factory(
        UserService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
        balances_log_repository,
    )

    ghoul_service = providers.Factory(
        GhoulService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
        notification_repository=scheduled_notification_repository,
        death_log_repository=death_log_repository,
    )

    cooldown_service = providers.Factory(
        CooldownService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
    )

    chat_service = providers.Factory(
        ChatService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
    )

    coffee_service = providers.Factory(
        CoffeeService,
        user_service=user_service,
        ghoul_service=ghoul_service,
        cooldown_service=cooldown_service,
    )

    lottery_service = providers.Factory(
        LotteryService,
        user_service=user_service,
        cooldown_service=cooldown_service,
        media_service=media_service,
        lottery_repository=lottery_repository,
    )

    stat_upgrade_service = providers.Factory(
        StatUpgradeService,
        ghoul_service=ghoul_service,
        user_service=user_service,
        dialog_service=dialog_service,
    )

    player_lookup_service = providers.Factory(
        PlayerLookupService,
        user_repo=user_repository,
        ghoul_repo=ghoul_repository,
    )
    ban_service = providers.Factory(
        BanService,
        user_repo=user_repository,
    )
    stats_edit_service = providers.Factory(
        StatsEditService,
        user_repo=user_repository,
        ghoul_repo=ghoul_repository,
        balances_log_repo=balances_log_repository,
    )

    reset_service = providers.Factory(
        ResetService,
        user_repo=user_repository,
        ghoul_repo=ghoul_repository,
    )

    rp_commands_repository = providers.Factory(RpCommandsRepository, session=db_session)

    rp_commands_service = providers.Singleton(
        RpCommandsService,
        rp_commands_repository_factory=rp_commands_repository.provider,
    )

    wordle_service = providers.Singleton(WordleService)

    wikipedia_service = providers.Factory(WikipediaService)

    transfer_service = providers.Factory(
        TransferService,
        user_repository=user_repository,
        transfer_repository=transfer_repository,
        balances_log_repository=balances_log_repository,
    )

    video_cutter_service = providers.Singleton(VideoCutterService)
    video_worker = providers.Singleton(VideoWorker, video_cutter_service)
