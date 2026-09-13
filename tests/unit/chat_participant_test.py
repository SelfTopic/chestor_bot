import pytest
from sqlalchemy import func, select

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.chat_participant import ChatParticipantRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.chat import ChatService
from src.bot.types.insert import ChatInsert
from src.database.models import ChatParticipant


@pytest.fixture
def chat_repo(session):
    return ChatRepository(session)


@pytest.fixture
def chat_participant_repo(session):
    return ChatParticipantRepository(session)


@pytest.fixture
def chat_service(session):
    return ChatService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
        chat_participant_repository=ChatParticipantRepository(session),
    )


@pytest.fixture
def make_chat(chat_repo):
    async def _make(telegram_id: int = 900_000_001):
        return await chat_repo.upsert(
            ChatInsert(
                telegram_id=telegram_id, title="Test chat", username=None, creator_id=None
            )
        )

    return _make


# --- ChatParticipantRepository -----------------------------------------------


async def test_upsert_then_get_random_returns_that_participant(
    chat_participant_repo, make_chat, make_user
):
    await make_chat(telegram_id=900_000_001)
    await make_user(telegram_id=700_000_001)

    await chat_participant_repo.upsert(chat_id=900_000_001, telegram_id=700_000_001)

    result = await chat_participant_repo.get_random_participant(900_000_001)
    assert result == 700_000_001


async def test_get_random_participant_returns_none_for_empty_chat(
    chat_participant_repo, make_chat
):
    await make_chat(telegram_id=900_000_002)

    result = await chat_participant_repo.get_random_participant(900_000_002)
    assert result is None


async def test_get_random_participant_only_picks_from_that_chat(
    chat_participant_repo, make_chat, make_user
):
    """Регрессия: два чата с разными участниками не должны смешиваться -
    случайный выбор в чате A никогда не должен вернуть участника чата B."""

    await make_chat(telegram_id=900_000_003)
    await make_chat(telegram_id=900_000_004)
    await make_user(telegram_id=700_000_003, username="tw_700003")
    await make_user(telegram_id=700_000_004, username="tw_700004")

    await chat_participant_repo.upsert(chat_id=900_000_003, telegram_id=700_000_003)
    await chat_participant_repo.upsert(chat_id=900_000_004, telegram_id=700_000_004)

    for _ in range(10):
        result = await chat_participant_repo.get_random_participant(900_000_003)
        assert result == 700_000_003


async def test_upsert_is_idempotent_for_same_pair(
    chat_participant_repo, make_chat, make_user, session
):
    """ON CONFLICT DO UPDATE - повторный upsert той же пары (chat_id,
    telegram_id) не должен падать/дублировать строку."""

    await make_chat(telegram_id=900_000_005)
    await make_user(telegram_id=700_000_005)

    await chat_participant_repo.upsert(chat_id=900_000_005, telegram_id=700_000_005)
    await chat_participant_repo.upsert(chat_id=900_000_005, telegram_id=700_000_005)

    count = await session.scalar(
        select(func.count()).select_from(ChatParticipant).where(
            ChatParticipant.chat_id == 900_000_005
        )
    )
    assert count == 1


# --- ChatService.get_random_participant --------------------------------------


async def test_chat_service_get_random_participant_returns_full_user(
    chat_service, make_chat, make_user
):
    await make_chat(telegram_id=900_000_006)
    await make_user(telegram_id=700_000_006, first_name="Ren")

    await chat_service.chat_participant_repository.upsert(
        chat_id=900_000_006, telegram_id=700_000_006
    )

    user = await chat_service.get_random_participant(900_000_006)
    assert user is not None
    assert user.telegram_id == 700_000_006
    assert user.first_name == "Ren"


async def test_chat_service_get_random_participant_none_when_empty(
    chat_service, make_chat
):
    await make_chat(telegram_id=900_000_007)

    user = await chat_service.get_random_participant(900_000_007)
    assert user is None
