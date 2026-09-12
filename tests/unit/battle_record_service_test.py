import pytest

from src.bot.repositories.active_battle import ActiveBattleRepository
from src.bot.repositories.battle import BattleRepository
from src.bot.services.battle_record import BattleRecordService


@pytest.fixture
def battle_record_service(session):
    return BattleRecordService(
        active_battle_repository=ActiveBattleRepository(session),
        battle_repository=BattleRepository(session),
    )


# --- try_claim_mob_fight / try_claim_duel - сама защита от эксплойта --------


async def test_try_claim_mob_fight_succeeds_when_free(battle_record_service, make_user):
    await make_user(telegram_id=500_000_001)
    assert await battle_record_service.try_claim_mob_fight(500_000_001) is True


async def test_try_claim_mob_fight_fails_when_already_busy(battle_record_service, make_user):
    await make_user(telegram_id=500_000_002)
    assert await battle_record_service.try_claim_mob_fight(500_000_002) is True
    # Вторая попытка занять того же самого гуля - должна провалиться,
    # первая бронь ещё активна (release не вызывался).
    assert await battle_record_service.try_claim_mob_fight(500_000_002) is False


async def test_try_claim_duel_claims_both_sides_atomically(battle_record_service, make_user):
    await make_user(telegram_id=500_000_003)
    await make_user(telegram_id=500_000_004, username="tw_500004")
    assert await battle_record_service.try_claim_duel(500_000_003, 500_000_004) is True
    assert await battle_record_service.is_busy(500_000_003) is True
    assert await battle_record_service.is_busy(500_000_004) is True


async def test_try_claim_duel_fails_and_rolls_back_when_one_side_already_busy(
    battle_record_service, make_user
):
    """Регрессия по мотивам чата: A уже занят (например, боем с мобом) -
    попытка втянуть его ЕЩЁ и в дуэль с B должна провалиться целиком, и
    B НЕ должен остаться "наполовину занятым" - иначе ровно тот эксплойт,
    от которого эта таблица и придумана (частичный захват хуже отказа)."""

    await make_user(telegram_id=500_000_005)  # A
    await make_user(telegram_id=500_000_006, username="tw_500006")  # B

    assert await battle_record_service.try_claim_mob_fight(500_000_005) is True  # A занят мобом

    claimed = await battle_record_service.try_claim_duel(500_000_005, 500_000_006)
    assert claimed is False

    # Ключевая проверка - B НЕ должен был остаться запертым из-за того,
    # что A уже был занят. Откат должен быть полным.
    assert await battle_record_service.is_busy(500_000_006) is False
    # А исходная бронь A (моб) должна остаться нетронутой.
    assert await battle_record_service.is_busy(500_000_005) is True


async def test_the_exact_exploit_scenario_from_the_chat(battle_record_service, make_user):
    """Твинк приглашает основного на дуэль, тот параллельно пытается
    начать бой с мобом - выигрывает только ОДНА попытка, вторая должна
    честно провалиться (а не тихо создать вторую независимую бронь)."""

    await make_user(telegram_id=500_000_007)  # основной
    await make_user(telegram_id=500_000_008, username="tw_500008")  # твинк

    duel_claimed = await battle_record_service.try_claim_duel(500_000_007, 500_000_008)
    assert duel_claimed is True

    # "Одновременно" пытается ещё и на моба - но уже занят дуэлью.
    mob_claimed = await battle_record_service.try_claim_mob_fight(500_000_007)
    assert mob_claimed is False


async def test_release_frees_up_participants_for_a_new_battle(battle_record_service, make_user):
    await make_user(telegram_id=500_000_009)
    await battle_record_service.try_claim_mob_fight(500_000_009)
    assert await battle_record_service.is_busy(500_000_009) is True

    await battle_record_service.release(500_000_009)

    assert await battle_record_service.is_busy(500_000_009) is False
    assert await battle_record_service.try_claim_mob_fight(500_000_009) is True


async def test_is_busy_false_for_a_ghoul_with_no_active_battle(battle_record_service, make_user):
    await make_user(telegram_id=500_000_010)
    assert await battle_record_service.is_busy(500_000_010) is False


# --- История: record_* / count_*_last_24h -----------------------------------


async def test_record_and_count_mob_fight(battle_record_service, make_user):
    await make_user(telegram_id=500_000_011)

    await battle_record_service.record_mob_fight(
        telegram_id=500_000_011, mob_name="Одичавший гуль", winner="a", ended_naturally=True
    )

    assert await battle_record_service.count_total_last_24h(500_000_011) == 1


async def test_record_and_count_duel_for_both_sides(battle_record_service, make_user):
    await make_user(telegram_id=500_000_012)
    await make_user(telegram_id=500_000_013, username="tw_500013")

    await battle_record_service.record_duel(
        telegram_id_a=500_000_012,
        telegram_id_b=500_000_013,
        winner="a",
        ended_naturally=True,
    )

    assert await battle_record_service.count_total_last_24h(500_000_012) == 1
    assert await battle_record_service.count_total_last_24h(500_000_013) == 1
    # Пара считается независимо от того, кто был "a", а кто "b" в записи.
    assert await battle_record_service.count_pair_last_24h(500_000_012, 500_000_013) == 1
    assert await battle_record_service.count_pair_last_24h(500_000_013, 500_000_012) == 1


async def test_count_total_last_24h_is_zero_with_no_history(battle_record_service, make_user):
    await make_user(telegram_id=500_000_014)
    assert await battle_record_service.count_total_last_24h(500_000_014) == 0
