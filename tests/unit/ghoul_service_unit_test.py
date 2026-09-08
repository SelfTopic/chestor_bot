import pytest

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.ghoul import GhoulService
from src.bot.types import KaguneType


@pytest.fixture
def ghoul_service(session):
    return GhoulService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
    )


async def test_get_returns_none_for_unknown(ghoul_service):
    result = await ghoul_service.get(find_by=999_999_999)
    assert result is None


async def test_get_by_telegram_id(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_001)
    await make_ghoul(telegram_id=200_000_001)
    result = await ghoul_service.get(find_by=200_000_001)
    assert result is not None
    assert result.telegram_id == 200_000_001


async def test_snap_finger_increments(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_100)
    await make_ghoul(telegram_id=200_000_100, snap_count=5)
    result = await ghoul_service.snap_finger(telegram_id=200_000_100)
    assert result.snap_count == 6


async def test_snap_finger_raises_for_unknown(ghoul_service):
    with pytest.raises(ValueError):
        await ghoul_service.snap_finger(telegram_id=999_999_002)


async def test_coffee_increments(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_200)
    await make_ghoul(telegram_id=200_000_200, coffee_count=3)
    result = await ghoul_service.coffee(telegram_id=200_000_200)
    assert result.coffee_count == 4


async def test_upgrade_kagune_increments_strength(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_300)
    await make_ghoul(
        telegram_id=200_000_300,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=2,
    )
    result = await ghoul_service.upgrade_kagune(telegram_id=200_000_300)
    assert result.kagune_strength_ukaku == 3


async def test_upgrade_kagune_with_explicit_type(ghoul_service, make_user, make_ghoul):
    """Явно указанный тип побеждает авто-определение - нужно для будущей
    клавиатуры выбора при нескольких открытых типах."""
    await make_user(telegram_id=200_000_301)
    await make_ghoul(
        telegram_id=200_000_301,
        kagune_type_bit=KaguneType.UKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"],
        kagune_strength_ukaku=5,
        kagune_strength_bikaku=1,
    )
    result = await ghoul_service.upgrade_kagune(
        telegram_id=200_000_301, kagune_type=KaguneType.BIKAKU
    )
    assert result.kagune_strength_bikaku == 2
    assert result.kagune_strength_ukaku == 5  # другой тип не тронут


async def test_upgrade_kagune_requires_explicit_type_when_multiple_owned(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=200_000_302)
    await make_ghoul(
        telegram_id=200_000_302,
        kagune_type_bit=KaguneType.UKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"],
        kagune_strength_ukaku=1,
        kagune_strength_bikaku=1,
    )
    with pytest.raises(ValueError, match="more than one"):
        await ghoul_service.upgrade_kagune(telegram_id=200_000_302)


async def test_upgrade_kagune_rejects_unowned_type(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_303)
    await make_ghoul(
        telegram_id=200_000_303,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=1,
    )
    with pytest.raises(ValueError, match="does not own"):
        await ghoul_service.upgrade_kagune(
            telegram_id=200_000_303, kagune_type=KaguneType.BIKAKU
        )


async def test_owned_kagune_types(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_304)
    ghoul = await make_ghoul(
        telegram_id=200_000_304,
        kagune_type_bit=KaguneType.UKAKU.value["bit"] | KaguneType.RINKAKU.value["bit"],
        kagune_strength_ukaku=1,
        kagune_strength_rinkaku=3,
    )
    owned = ghoul_service.owned_kagune_types(ghoul)
    assert set(owned) == {KaguneType.UKAKU, KaguneType.RINKAKU}


async def test_total_kagune_strength_sums_all_owned_types(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=200_000_305)
    ghoul = await make_ghoul(
        telegram_id=200_000_305,
        kagune_type_bit=KaguneType.UKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"],
        kagune_strength_ukaku=4,
        kagune_strength_bikaku=6,
    )
    assert ghoul_service.total_kagune_strength(ghoul) == 10


async def test_get_top_kagune_by_specific_type_excludes_unowned(
    ghoul_service, make_user, make_ghoul
):
    """Топ по конкретному типу не должен включать тех, у кого этот тип
    вообще не открыт (NULL) - иначе они бы ложно попали в топ с нулём."""
    await make_user(telegram_id=200_000_320, username="topkagune_320")
    await make_ghoul(
        telegram_id=200_000_320,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=50,
    )
    await make_user(telegram_id=200_000_321, username="topkagune_321")
    await make_ghoul(
        telegram_id=200_000_321,
        kagune_type_bit=KaguneType.BIKAKU.value["bit"],
        kagune_strength_bikaku=999,
    )

    top = await ghoul_service.get_top_kagune(20, kagune_type=KaguneType.UKAKU)

    assert [g.telegram_id for g in top] == [200_000_320]


async def test_get_top_kagune_by_specific_type_orders_descending(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=200_000_322, username="topkagune_322")
    await make_ghoul(
        telegram_id=200_000_322,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=5,
    )
    await make_user(telegram_id=200_000_323, username="topkagune_323")
    await make_ghoul(
        telegram_id=200_000_323,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=25,
    )

    top = await ghoul_service.get_top_kagune(20, kagune_type=KaguneType.UKAKU)

    assert [g.telegram_id for g in top] == [200_000_323, 200_000_322]


async def test_get_top_kagune_without_type_still_sorts_by_sum(
    ghoul_service, make_user, make_ghoul
):
    """Регрессия: старое поведение (без указания типа) не должно было
    сломаться после добавления параметра kagune_type."""
    await make_user(telegram_id=200_000_324, username="topkagune_324")
    await make_ghoul(
        telegram_id=200_000_324,
        kagune_type_bit=KaguneType.UKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"],
        kagune_strength_ukaku=3,
        kagune_strength_bikaku=3,
    )
    await make_user(telegram_id=200_000_325, username="topkagune_325")
    await make_ghoul(
        telegram_id=200_000_325,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=100,
    )

    top = await ghoul_service.get_top_kagune(20)

    assert [g.telegram_id for g in top][:2] == [200_000_325, 200_000_324]


async def test_register_assigns_initial_strength_to_chosen_type(
    ghoul_service, make_user
):
    await make_user(telegram_id=200_000_306)
    result = await ghoul_service.register(telegram_id=200_000_306)
    ghoul = result.ghoul

    owned = ghoul_service.owned_kagune_types(ghoul)
    assert len(owned) == 1
    assert ghoul_service.get_kagune_strength(ghoul, owned[0]) == 1


# --- Управление типами кагуне через creator-команды ---


async def test_grant_kagune_type_sets_bit_and_strength(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=200_000_310)
    await make_ghoul(
        telegram_id=200_000_310,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=5,
    )

    ghoul = await ghoul_service.grant_kagune_type(200_000_310, KaguneType.BIKAKU)

    assert ghoul.kagune_strength_bikaku == 1
    assert ghoul.kagune_type_bit == (
        KaguneType.UKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"]
    )
    assert set(ghoul_service.owned_kagune_types(ghoul)) == {
        KaguneType.UKAKU,
        KaguneType.BIKAKU,
    }


async def test_grant_kagune_type_rejects_already_owned(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=200_000_311)
    await make_ghoul(
        telegram_id=200_000_311,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=1,
    )

    with pytest.raises(ValueError, match="already owns"):
        await ghoul_service.grant_kagune_type(200_000_311, KaguneType.UKAKU)


async def test_grant_all_kagune_types_fills_only_missing(
    ghoul_service, make_user, make_ghoul
):
    """Уже открытый тип не должен сбрасываться обратно к initial_strength."""
    await make_user(telegram_id=200_000_312)
    await make_ghoul(
        telegram_id=200_000_312,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=50,
    )

    ghoul = await ghoul_service.grant_all_kagune_types(200_000_312)

    assert ghoul.kagune_strength_ukaku == 50  # не тронут
    assert ghoul.kagune_strength_koukaku == 1
    assert ghoul.kagune_strength_rinkaku == 1
    assert ghoul.kagune_strength_bikaku == 1
    assert len(ghoul_service.owned_kagune_types(ghoul)) == 4


async def test_revoke_kagune_type_clears_bit_and_strength(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=200_000_313)
    await make_ghoul(
        telegram_id=200_000_313,
        kagune_type_bit=KaguneType.UKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"],
        kagune_strength_ukaku=1,
        kagune_strength_bikaku=10,
    )

    ghoul = await ghoul_service.revoke_kagune_type(200_000_313, KaguneType.BIKAKU)

    assert ghoul.kagune_strength_bikaku is None
    assert ghoul.kagune_type_bit == KaguneType.UKAKU.value["bit"]
    assert ghoul_service.owned_kagune_types(ghoul) == [KaguneType.UKAKU]


async def test_revoke_kagune_type_rejects_unowned(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_314)
    await make_ghoul(
        telegram_id=200_000_314,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=1,
    )

    with pytest.raises(ValueError, match="does not own"):
        await ghoul_service.revoke_kagune_type(200_000_314, KaguneType.BIKAKU)


async def test_revoke_kagune_type_rejects_removing_the_last_one(
    ghoul_service, make_user, make_ghoul
):
    await make_user(telegram_id=200_000_315)
    await make_ghoul(
        telegram_id=200_000_315,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=1,
    )

    with pytest.raises(ValueError, match="last remaining"):
        await ghoul_service.revoke_kagune_type(200_000_315, KaguneType.UKAKU)


async def test_register_creates_ghoul(ghoul_service, make_user):
    await make_user(telegram_id=200_000_400)
    result = await ghoul_service.register(telegram_id=200_000_400)
    assert result.ok is True
    assert result.ghoul is not None


async def test_register_fails_if_already_exists(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_401)
    await make_ghoul(telegram_id=200_000_401)
    result = await ghoul_service.register(telegram_id=200_000_401)
    assert result.ok is False


async def test_calculate_power(ghoul_service, make_user, make_ghoul):
    await make_user(telegram_id=200_000_500)
    ghoul = await make_ghoul(
        telegram_id=200_000_500,
        strength=10,
        dexterity=10,
        speed=10,
        max_health=10,
        regeneration=10,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=10,
    )
    power = ghoul_service.calculate_power(ghoul)
    assert power == 60


@pytest.mark.parametrize(
    "power,expected_rank",
    [
        (0, "F"),
        (499, "F"),
        (500, "D"),
        (999, "D"),
        (1000, "C"),
        (1999, "B"),
        (2000, "A"),
        (3499, "A"),
        (3500, "S"),
        (4999, "S"),
        (5000, "SS"),
        (7499, "SS"),
        (7500, "SSS"),
        (10000, "SSS+"),
    ],
)
def test_get_danger_rank(ghoul_service, power, expected_rank):
    assert ghoul_service.get_danger_rank(power) == expected_rank
