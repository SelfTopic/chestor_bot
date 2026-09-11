from src.bot.routers.ghoul_routers.mob_fight_preview import (
    _snapshot_from_ghoul,
    _snapshot_power,
)
from src.bot.types import KaguneType
from src.database.models import Ghoul


class FakeGhoulService:
    """Минимальный дублёр GhoulService - тем же методам и тем же способом,
    что в race_profile_rich_message_test.py: тесту нужны только эти два
    метода, без БД."""

    def owned_kagune_types(self, ghoul: Ghoul):
        return [
            kt for kt in KaguneType if getattr(ghoul, kt.value["strength_column"]) is not None
        ]

    def get_kagune_strength(self, ghoul: Ghoul, kagune_type: KaguneType):
        return getattr(ghoul, kagune_type.value["strength_column"])


def make_ghoul(
    strength: int = 100,
    dexterity: int = 100,
    speed: int = 100,
    regeneration: int = 100,
    health: int = 50,
    max_health: int = 200,
    hunger: int = 80,
    is_kakuja: bool = False,
    kagune_strength_ukaku: "int | None" = None,
    kagune_strength_koukaku: "int | None" = None,
    kagune_strength_rinkaku: "int | None" = None,
    kagune_strength_bikaku: "int | None" = None,
) -> Ghoul:
    return Ghoul(
        id=7,
        telegram_id=1,
        strength=strength,
        dexterity=dexterity,
        speed=speed,
        regeneration=regeneration,
        health=health,
        max_health=max_health,
        hunger=hunger,
        is_kakuja=is_kakuja,
        kagune_strength_ukaku=kagune_strength_ukaku,
        kagune_strength_koukaku=kagune_strength_koukaku,
        kagune_strength_rinkaku=kagune_strength_rinkaku,
        kagune_strength_bikaku=kagune_strength_bikaku,
    )


def test_snapshot_from_ghoul_maps_stats_and_uses_max_health_not_current():
    # health (может быть урезано предыдущим боем) НЕ используется - в бой
    # идёт полный пул max_health, см. docstring _snapshot_from_ghoul.
    ghoul = make_ghoul(strength=123, dexterity=45, speed=67, regeneration=89, health=1, max_health=500)

    snapshot = _snapshot_from_ghoul(ghoul, "chestor", FakeGhoulService())

    assert snapshot.name == "chestor"
    assert snapshot.strength == 123
    assert snapshot.dexterity == 45
    assert snapshot.speed == 67
    assert snapshot.regeneration == 89
    assert snapshot.health == 500


def test_snapshot_from_ghoul_only_includes_owned_kagune_types():
    ghoul = make_ghoul(kagune_strength_ukaku=18, kagune_strength_bikaku=10)

    snapshot = _snapshot_from_ghoul(ghoul, "chestor", FakeGhoulService())

    assert snapshot.kagune_strength == {KaguneType.UKAKU: 18, KaguneType.BIKAKU: 10}


def test_snapshot_from_ghoul_with_no_kagune_gives_empty_dict():
    ghoul = make_ghoul()
    snapshot = _snapshot_from_ghoul(ghoul, "chestor", FakeGhoulService())
    assert snapshot.kagune_strength == {}


def test_snapshot_power_sums_stats_and_kagune_strength():
    ghoul = make_ghoul(
        strength=10, dexterity=20, speed=30, regeneration=40, max_health=50,
        kagune_strength_ukaku=5,
    )
    snapshot = _snapshot_from_ghoul(ghoul, "chestor", FakeGhoulService())

    # 10+20+30+50+40 (статы+HP) + 5 (кагуне)
    assert _snapshot_power(snapshot) == 155
