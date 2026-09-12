import pytest

from src.bot.repositories.duel_session import DuelSessionRepository
from src.bot.services.duel import DuelService


@pytest.fixture
def duel_service(session):
    return DuelService(DuelSessionRepository(session))


async def test_create_starts_in_awaiting_consent_stage(duel_service, make_user):
    await make_user(telegram_id=600_000_001)
    await make_user(telegram_id=600_000_002, username="tw_600002")

    duel_session = await duel_service.create(
        chat_id=-1001, initiator_telegram_id=600_000_001, target_telegram_id=600_000_002
    )

    assert duel_session.stage == "awaiting_consent"
    assert duel_session.initiator_consented is False
    assert duel_session.target_consented is False
    assert duel_session.chat_id == -1001
    assert duel_session.is_private_origin is False


async def test_create_persists_is_private_origin(duel_service, make_user):
    """Дуэль, вызванная из ЛС инициатора с ботом (@username без общего
    группового чата) - соперник не состоит в этом чате и никогда не
    увидит там ни кнопки, ни лог боя (см. чат, найдено как баг при
    ревью) - роутер обязан знать об этом заранее, чтобы дублировать
    отправку в оба личных чата."""

    await make_user(telegram_id=600_000_015)
    await make_user(telegram_id=600_000_016, username="tw_600016")

    duel_session = await duel_service.create(
        chat_id=600_000_015,
        initiator_telegram_id=600_000_015,
        target_telegram_id=600_000_016,
        is_private_origin=True,
    )

    assert duel_session.is_private_origin is True


async def test_get_returns_the_created_session(duel_service, make_user):
    await make_user(telegram_id=600_000_003)
    await make_user(telegram_id=600_000_004, username="tw_600004")
    created = await duel_service.create(
        chat_id=1, initiator_telegram_id=600_000_003, target_telegram_id=600_000_004
    )

    fetched = await duel_service.get(created.id)

    assert fetched is not None
    assert fetched.id == created.id


async def test_get_returns_none_for_missing_id(duel_service):
    assert await duel_service.get(999_999_999) is None


async def test_atomic_update_sets_field_without_changing_stage(duel_service, make_user):
    await make_user(telegram_id=600_000_005)
    await make_user(telegram_id=600_000_006, username="tw_600006")
    created = await duel_service.create(
        chat_id=1, initiator_telegram_id=600_000_005, target_telegram_id=600_000_006
    )

    updated = await duel_service.atomic_update(
        created.id, "awaiting_consent", initiator_consented=True
    )

    assert updated is not None
    assert updated.initiator_consented is True
    assert updated.target_consented is False
    assert updated.stage == "awaiting_consent"


async def test_atomic_update_fails_when_stage_does_not_match(duel_service, make_user):
    await make_user(telegram_id=600_000_007)
    await make_user(telegram_id=600_000_008, username="tw_600008")
    created = await duel_service.create(
        chat_id=1, initiator_telegram_id=600_000_007, target_telegram_id=600_000_008
    )

    result = await duel_service.atomic_update(
        created.id, "awaiting_winner_choice", stage="done"
    )

    assert result is None
    # Стадия не должна была измениться из-за проигранной проверки.
    still_there = await duel_service.get(created.id)
    assert still_there.stage == "awaiting_consent"


async def test_atomic_update_only_the_first_of_two_calls_wins(duel_service, make_user):
    """Регрессия по существу самой защиты от гонки "нажатие кнопки против
    сработавшего таймаута": как только один вызов перевёл стадию, второй
    вызов с тем же expected_stage обязан честно проиграть (None), а не
    применить действие повторно поверх уже нового состояния."""

    await make_user(telegram_id=600_000_009)
    await make_user(telegram_id=600_000_010, username="tw_600010")
    created = await duel_service.create(
        chat_id=1, initiator_telegram_id=600_000_009, target_telegram_id=600_000_010
    )

    first = await duel_service.atomic_update(created.id, "awaiting_consent", stage="done")
    second = await duel_service.atomic_update(created.id, "awaiting_consent", stage="done")

    assert first is not None
    assert second is None


async def test_find_active_for_returns_session_for_either_participant(duel_service, make_user):
    await make_user(telegram_id=600_000_011)
    await make_user(telegram_id=600_000_012, username="tw_600012")
    created = await duel_service.create(
        chat_id=1, initiator_telegram_id=600_000_011, target_telegram_id=600_000_012
    )

    found_by_initiator = await duel_service.find_active_for(600_000_011)
    found_by_target = await duel_service.find_active_for(600_000_012)

    assert found_by_initiator is not None and found_by_initiator.id == created.id
    assert found_by_target is not None and found_by_target.id == created.id


async def test_find_active_for_excludes_done_sessions(duel_service, make_user):
    await make_user(telegram_id=600_000_013)
    await make_user(telegram_id=600_000_014, username="tw_600014")
    created = await duel_service.create(
        chat_id=1, initiator_telegram_id=600_000_013, target_telegram_id=600_000_014
    )
    await duel_service.atomic_update(created.id, "awaiting_consent", stage="done")

    assert await duel_service.find_active_for(600_000_013) is None
