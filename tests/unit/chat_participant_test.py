from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.chat_participant import ChatParticipantRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.chat import ChatService
from src.bot.types.insert import ChatInsert
from src.bot.utils import utcnow_naive
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


async def _backdate_last_seen(session, chat_id: int, telegram_id: int, when: datetime) -> None:
    """Тестовый хелпер - подделывает `last_seen_at` в прошлое, чтобы
    проверить ленивый сброс календарных счётчиков без реального ожидания."""

    await session.execute(
        update(ChatParticipant)
        .where(
            ChatParticipant.chat_id == chat_id, ChatParticipant.telegram_id == telegram_id
        )
        .values(last_seen_at=when)
    )


async def _get_row(session, chat_id: int, telegram_id: int) -> ChatParticipant:
    row = await session.get(ChatParticipant, {"chat_id": chat_id, "telegram_id": telegram_id})
    assert row is not None
    return row


# --- record_message / get_random_participant ---------------------------------


async def test_record_message_then_get_random_returns_that_participant(
    chat_participant_repo, make_chat, make_user
):
    await make_chat(telegram_id=900_000_001)
    await make_user(telegram_id=700_000_001)

    await chat_participant_repo.record_message(chat_id=900_000_001, telegram_id=700_000_001)

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

    await chat_participant_repo.record_message(chat_id=900_000_003, telegram_id=700_000_003)
    await chat_participant_repo.record_message(chat_id=900_000_004, telegram_id=700_000_004)

    for _ in range(10):
        result = await chat_participant_repo.get_random_participant(900_000_003)
        assert result == 700_000_003


async def test_record_message_is_idempotent_for_same_pair(
    chat_participant_repo, make_chat, make_user, session
):
    """ON CONFLICT DO UPDATE - повторный вызов для той же пары (chat_id,
    telegram_id) не должен падать/дублировать строку."""

    await make_chat(telegram_id=900_000_005)
    await make_user(telegram_id=700_000_005)

    await chat_participant_repo.record_message(chat_id=900_000_005, telegram_id=700_000_005)
    await chat_participant_repo.record_message(chat_id=900_000_005, telegram_id=700_000_005)

    count = await session.scalar(
        select(func.count()).select_from(ChatParticipant).where(
            ChatParticipant.chat_id == 900_000_005
        )
    )
    assert count == 1


# --- record_message - счётчики и календарный сброс ---------------------------


async def test_record_message_first_time_sets_all_counters_to_one(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_010)
    await make_user(telegram_id=700_000_010)

    await chat_participant_repo.record_message(chat_id=900_000_010, telegram_id=700_000_010)

    row = await _get_row(session, 900_000_010, 700_000_010)
    assert (row.messages_total, row.messages_today, row.messages_week, row.messages_month) == (
        1,
        1,
        1,
        1,
    )


async def test_record_message_within_same_day_increments_all_counters(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_011)
    await make_user(telegram_id=700_000_011)

    await chat_participant_repo.record_message(chat_id=900_000_011, telegram_id=700_000_011)
    await chat_participant_repo.record_message(chat_id=900_000_011, telegram_id=700_000_011)
    await chat_participant_repo.record_message(chat_id=900_000_011, telegram_id=700_000_011)

    row = await _get_row(session, 900_000_011, 700_000_011)
    assert (row.messages_total, row.messages_today, row.messages_week, row.messages_month) == (
        3,
        3,
        3,
        3,
    )


async def test_record_message_next_day_resets_only_daily_counter(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_012)
    await make_user(telegram_id=700_000_012)

    await chat_participant_repo.record_message(chat_id=900_000_012, telegram_id=700_000_012)
    await chat_participant_repo.record_message(chat_id=900_000_012, telegram_id=700_000_012)

    # Откатываем last_seen_at на вчера (та же неделя/месяц, если тест не
    # запущен ровно в понедельник/1-е число - крайне маловероятно, но
    # честно: если запущен, week/month тоже честно сбросятся, это не
    # ломает проверку day-сброса ниже).
    await _backdate_last_seen(
        session, 900_000_012, 700_000_012, utcnow_naive() - timedelta(days=1)
    )

    await chat_participant_repo.record_message(chat_id=900_000_012, telegram_id=700_000_012)

    row = await _get_row(session, 900_000_012, 700_000_012)
    assert row.messages_today == 1
    assert row.messages_total == 3


async def test_record_message_next_month_resets_month_but_keeps_total(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_013)
    await make_user(telegram_id=700_000_013)

    await chat_participant_repo.record_message(chat_id=900_000_013, telegram_id=700_000_013)
    await chat_participant_repo.record_message(chat_id=900_000_013, telegram_id=700_000_013)

    await _backdate_last_seen(
        session, 900_000_013, 700_000_013, utcnow_naive() - timedelta(days=40)
    )

    await chat_participant_repo.record_message(chat_id=900_000_013, telegram_id=700_000_013)

    row = await _get_row(session, 900_000_013, 700_000_013)
    assert row.messages_month == 1
    assert row.messages_week == 1
    assert row.messages_today == 1
    assert row.messages_total == 3


# --- record_join --------------------------------------------------------------


async def test_record_join_creates_row_with_join_info(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_020)
    await make_user(telegram_id=700_000_020)

    joined_at = datetime(2026, 1, 1, 12, 0, 0)
    await chat_participant_repo.record_join(
        chat_id=900_000_020,
        telegram_id=700_000_020,
        joined_at=joined_at,
        join_method="invite_link",
    )

    row = await _get_row(session, 900_000_020, 700_000_020)
    assert row.joined_at == joined_at
    assert row.join_method == "invite_link"
    assert row.messages_total == 0


async def test_record_join_does_not_reset_existing_message_counters(
    chat_participant_repo, make_chat, make_user, session
):
    """Порядок "сначала написал, потом событие входа поймали" - редкий, но
    возможный (например бот пропустил апдейт) - join не должен обнулить
    уже накопленную статистику сообщений."""

    await make_chat(telegram_id=900_000_021)
    await make_user(telegram_id=700_000_021)

    await chat_participant_repo.record_message(chat_id=900_000_021, telegram_id=700_000_021)
    await chat_participant_repo.record_message(chat_id=900_000_021, telegram_id=700_000_021)

    await chat_participant_repo.record_join(
        chat_id=900_000_021,
        telegram_id=700_000_021,
        joined_at=datetime(2026, 1, 1),
        join_method="self",
    )

    row = await _get_row(session, 900_000_021, 700_000_021)
    assert row.messages_total == 2
    assert row.join_method == "self"


# --- remove ---------------------------------------------------------------


async def test_remove_deletes_the_row(chat_participant_repo, make_chat, make_user, session):
    await make_chat(telegram_id=900_000_030)
    await make_user(telegram_id=700_000_030)
    await chat_participant_repo.record_message(chat_id=900_000_030, telegram_id=700_000_030)

    await chat_participant_repo.remove(chat_id=900_000_030, telegram_id=700_000_030)

    row = await session.get(
        ChatParticipant, {"chat_id": 900_000_030, "telegram_id": 700_000_030}
    )
    assert row is None


async def test_remove_is_a_noop_when_nothing_to_remove(chat_participant_repo, make_chat):
    await make_chat(telegram_id=900_000_031)

    # Не должно падать, даже если строки никогда не было.
    await chat_participant_repo.remove(chat_id=900_000_031, telegram_id=1)


# --- ChatService.get_random_participant --------------------------------------


async def test_chat_service_get_random_participant_returns_full_user(
    chat_service, make_chat, make_user
):
    await make_chat(telegram_id=900_000_006)
    await make_user(telegram_id=700_000_006, first_name="Ren")

    await chat_service.chat_participant_repository.record_message(
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
