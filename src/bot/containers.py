from aiogram import Bot

from dependency_injector import containers, providers 

from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

from .services import (
    UserService,
    DialogService,
    SyncEntitiesService,
    GhoulService,
    CooldownService
)

from .repositories import (
    UserRepository,
    GhoulRepository,
    UserCooldownRepository
)

session_context: ContextVar[AsyncSession] = ContextVar("session_context")

class Container(containers.DeclarativeContainer):

    config = providers.Configuration()
    bot = providers.Dependency(instance_of=Bot)

    db_session = providers.Factory(lambda: session_context.get())

    user_repository = providers.Factory(UserRepository, session=db_session)
    ghoul_repository = providers.Factory(GhoulRepository, session=db_session)

    user_cooldown_repository = providers.Factory(
        UserCooldownRepository,
        session=db_session
    )

    dialog_service = providers.Factory(DialogService)
    user_service = providers.Factory(
        UserService, 
        user_repository,
        ghoul_repository,
        user_cooldown_repository
    )

    sync_entities_service = providers.Factory(
        SyncEntitiesService, 
        user_repository,
        ghoul_repository,
        user_cooldown_repository
    )

    ghoul_service = providers.Factory(
        GhoulService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository
    )

    cooldown_service = providers.Factory(
        CooldownService,
        user_repository,
        ghoul_repository,
        user_cooldown_repository    
    )