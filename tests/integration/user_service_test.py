import pytest
from src.bot.repositories.user import UserRepository
from src.bot.services.user import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import User

@pytest.mark.asyncio
async def test_user_service(session: AsyncSession):

    repo = UserRepository(session=session)

    service = UserService(
        userRepository=repo 
    )

    # Create fake user

    mock_user = User(
        id=123,
        is_bot=False,
        first_name="Alex",
        last_name=None,
        username="alex_tg"
    )

    # And register in database

    user = await service.upsert(mock_user)

    assert user 
    assert user.first_name == "Alex"
    assert user.telegram_id == 123
    assert user.username == "alex_tg"
    assert user.last_name == None 

    # Test change user data 

    mock_user_changed = User(
        id=123, # Same user
        is_bot=False,
        first_name="Alex",
        last_name="Smith", # Set last name
        username="alex_tg_off" # Change username
    )

    changed_user = await service.upsert(mock_user_changed)

    assert changed_user
    assert changed_user.first_name == "Alex"
    assert changed_user.last_name == "Smith"
    assert changed_user.username == "alex_tg_off"

    # Create fake bot 

    mock_bot = User(
        id=123,
        is_bot=True,
        first_name="Alex Bot",
        last_name=None,
        username="alex_tg_bot"
    )


    # And register in database

    bot = await service.upsert(mock_bot)

    # Service don't register bots

    assert bot == None




