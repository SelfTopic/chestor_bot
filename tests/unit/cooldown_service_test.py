import pytest

from src.bot.repositories import (
    ChatRepository,
    GhoulRepository,
    UserCooldownRepository,
    UserRepository,
)
from src.bot.services.cooldown import CooldownService


@pytest.fixture
def cooldown_service(session):
    return CooldownService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
    )


@pytest.fixture
def cooldown_repo(session):
    return UserCooldownRepository(session)


@pytest.fixture
async def seed_cooldown_type(cooldown_repo):
    async def _seed(name: str = "TEST_COOLDOWN", duration: int = 600):
        return await cooldown_repo.add_cooldown_type(name, duration)

    return _seed


# --- clear_cooldown ----------------------------------------------------------


# --- clear_all_cooldowns ------------------------------------------------------


async def test_clear_all_cooldowns_removes_every_type_for_that_user_only(
    cooldown_service, make_user, seed_cooldown_type
):
    await make_user(telegram_id=600_000_004)
    await make_user(telegram_id=600_000_005, username="tw_600005")
    await seed_cooldown_type("TEST_COOLDOWN_A", duration=600)
    await seed_cooldown_type("TEST_COOLDOWN_B", duration=600)

    await cooldown_service.set_cooldown(telegram_id=600_000_004, cooldown_type="TEST_COOLDOWN_A")
    await cooldown_service.set_cooldown(telegram_id=600_000_004, cooldown_type="TEST_COOLDOWN_B")
    # Другой пользователь с тем же типом - не должен пострадать.
    await cooldown_service.set_cooldown(telegram_id=600_000_005, cooldown_type="TEST_COOLDOWN_A")

    count = await cooldown_service.clear_all_cooldowns(600_000_004)

    assert count == 2
    assert await cooldown_service.is_end_cooldown(600_000_004, "TEST_COOLDOWN_A") is False
    assert await cooldown_service.is_end_cooldown(600_000_004, "TEST_COOLDOWN_B") is False
    # Второй пользователь - кулдаун цел, задело только первого.
    assert await cooldown_service.is_end_cooldown(600_000_005, "TEST_COOLDOWN_A") is True


# --- list_cooldown_types ------------------------------------------------------


async def test_list_cooldown_types_returns_seeded_names(cooldown_service, seed_cooldown_type):
    await seed_cooldown_type("TEST_COOLDOWN_X", duration=60)
    await seed_cooldown_type("TEST_COOLDOWN_Y", duration=120)

    names = await cooldown_service.list_cooldown_types()

    assert "TEST_COOLDOWN_X" in names
    assert "TEST_COOLDOWN_Y" in names
