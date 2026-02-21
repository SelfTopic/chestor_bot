from contextvars import ContextVar

from aiogram import Bot
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from .repositories import (
    ChatRepository,
    GhoulRepository,
    MediaRepository,
    UserCooldownRepository,
    UserRepository,
)
from .services import (
    ChatService,
    CooldownService,
    DialogService,
    GhoulQuizService,
    GhoulService,
    MediaDownloader,
    MediaService,
    SyncEntitiesService,
    UserService,
)
from .services.ghoul_game import CoffeeService

session_context: ContextVar[AsyncSession] = ContextVar("session_context")


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    bot = providers.Dependency(instance_of=Bot)

    db_session = providers.Factory(lambda: session_context.get())

    user_repository = providers.Factory(UserRepository, session=db_session)
    ghoul_repository = providers.Factory(GhoulRepository, session=db_session)

    user_cooldown_repository = providers.Factory(
        UserCooldownRepository, session=db_session
    )
    chat_repository = providers.Factory(ChatRepository, session=db_session)

    media_repository = providers.Factory(MediaRepository, session=db_session)

    dialog_service = providers.Factory(DialogService)

    media_downloader = providers.Factory(MediaDownloader, bot=bot)

    media_service = providers.Factory(
        MediaService, downloader=media_downloader, media_repository=media_repository
    )

    user_service = providers.Factory(
        UserService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
    )

    sync_entities_service = providers.Factory(
        SyncEntitiesService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
    )

    ghoul_service = providers.Factory(
        GhoulService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
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
        media_service=media_service,
        dialog_service=dialog_service,
    )

    ghoul_quiz_service = providers.Factory(GhoulQuizService)
