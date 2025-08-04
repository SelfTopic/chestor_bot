from aiogram import Bot

from dependency_injector import containers, providers 

from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

from .services import (
    UserService,
    DialogService,
    SyncEntitiesService    
)

from .repositories import (
    UserRepository    
)

session_context: ContextVar[AsyncSession] = ContextVar("session_context")

class Container(containers.DeclarativeContainer):

    config = providers.Configuration()
    bot = providers.Dependency(instance_of=Bot)

    db_session = providers.Factory(lambda: session_context.get())

    user_repository = providers.Factory(UserRepository, session=db_session)

    dialog_service = providers.Factory(DialogService)
    user_service = providers.Factory(UserService, user_repository)
    sync_entities_service = providers.Factory(SyncEntitiesService, user_repository)