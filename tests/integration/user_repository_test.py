import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_user_lifecycle(session: AsyncSession):

    repo = UserRepository(session)

    # Creating user
    user = await repo.upsert(
        telegram_id=123,
        first_name="Anna",
        last_name="Smith",
        username="anna"
    )
    
    assert user.first_name == "Anna"

    # Find by ID
    found_by_id = await repo.get(123)

    assert found_by_id
    assert found_by_id.username == "anna"

    # Find by username
    found_by_username = await repo.get("anna")

    assert found_by_username
    assert found_by_username.telegram_id == 123

    # Update
    await repo.upsert(
        telegram_id=123,
        first_name="Ann",
        username="ann",
        last_name="Smith"
    )

    updated_user = await repo.get(123)


    assert updated_user
    assert updated_user.first_name == "Ann"
    assert updated_user.username == "ann"
    assert updated_user.last_name == "Smith"

    # last name and username equal None
    await repo.upsert(
        telegram_id=123,
        first_name="ann"     
    )

    updated_user = await repo.get(123)

    assert updated_user
    assert updated_user.telegram_id == 123
    assert updated_user.first_name == "ann"
    assert updated_user.last_name == None 
    assert updated_user.username == None 

    none_user = await repo.get("undefined")

    assert none_user == None

    exist_user = await repo.exists(123)

    assert exist_user == True 

    not_exists_user = await repo.exists(2345)

    assert not_exists_user == False
    
