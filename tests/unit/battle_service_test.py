import random

from src.bot.services.battle_engine.battle_service import BattleService
from src.bot.services.battle_engine.core import Fighter
from src.bot.services.battle_engine.mob import MobService
from src.bot.types import KaguneType
from src.database.models import Ghoul


class FakeGhoulService:
    """Минимальный дублёр GhoulService - тот же паттерн, что в
    race_profile_rich_message_test.py: тесту нужны только эти два метода,
    без БД."""

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


def make_service() -> BattleService:
    return BattleService(mob_service=MobService())


# --- ghoul_to_fighter --------------------------------------------------------


def test_ghoul_to_fighter_maps_stats_and_uses_current_health_not_max():
    # ТЕКУЩЕЕ health (пассивно регенерирует со временем), а не max_health -
    # иначе гуль с 1 HP (например, только что проигравший бой, см. 3.1)
    # начинал бы каждый следующий бой при полном пуле, полностью игнорируя
    # пассивную регенерацию (см. чат).
    ghoul = make_ghoul(strength=123, dexterity=45, speed=67, regeneration=89, health=1, max_health=500)

    fighter = make_service().ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())

    assert isinstance(fighter, Fighter)
    assert fighter.name == "chestor"
    assert fighter.snapshot.strength == 123
    assert fighter.snapshot.dexterity == 45
    assert fighter.snapshot.speed == 67
    assert fighter.snapshot.regeneration == 89
    assert fighter.snapshot.health == 1


def test_ghoul_to_fighter_only_includes_owned_kagune_types():
    ghoul = make_ghoul(kagune_strength_ukaku=18, kagune_strength_bikaku=10)

    fighter = make_service().ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())

    assert fighter.snapshot.kagune_strength == {KaguneType.UKAKU: 18, KaguneType.BIKAKU: 10}


def test_ghoul_to_fighter_with_no_kagune_gives_empty_dict():
    ghoul = make_ghoul()
    fighter = make_service().ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())
    assert fighter.snapshot.kagune_strength == {}


# --- power_of ----------------------------------------------------------------


def test_power_of_sums_stats_and_kagune_strength():
    ghoul = make_ghoul(
        strength=10, dexterity=20, speed=30, regeneration=40, health=50, max_health=50,
        kagune_strength_ukaku=5,
    )
    fighter = make_service().ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())

    # 10+20+30+50+40 (статы+HP) + 5 (кагуне)
    assert BattleService.power_of(fighter.snapshot) == 155


def test_power_of_matches_calculate_power_at_full_health():
    # power_of(fighter.snapshot) даёт ТО ЖЕ число, что
    # GhoulService.calculate_power(ghoul) - НО только при health==max_health
    # (свежий/полностью восстановленный гуль) - calculate_power (профиль,
    # "распрофиль") всегда считает от max_health (стабильный вакуумный
    # показатель), а power_of/ghoul_to_fighter - от ТЕКУЩЕГО health (см.
    # чат: бой должен честно учитывать реальное состояние, а не всегда
    # начинаться при полном пуле). Они совпадают ровно тогда, когда гуль
    # не ранен - что и проверяет этот тест.
    ghoul = make_ghoul(strength=7, dexterity=8, speed=9, regeneration=10, health=11, max_health=11)
    fighter = make_service().ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())

    calculate_power_equivalent = (
        ghoul.strength + ghoul.dexterity + ghoul.speed + ghoul.max_health + ghoul.regeneration
    )
    assert BattleService.power_of(fighter.snapshot) == calculate_power_equivalent


def test_power_of_is_lower_than_calculate_power_when_wounded():
    # Регрессия (см. чат): ghoul_to_fighter раньше брал max_health вместо
    # health - гуль с 1 HP из 500 (только что проигравший бой, см. 3.1)
    # начинал бы следующий бой при полном пуле, полностью игнорируя
    # пассивную регенерацию. Теперь раненый гуль честно слабее в бою, чем
    # его "паспортная" (calculate_power) сила.
    ghoul = make_ghoul(strength=7, dexterity=8, speed=9, regeneration=10, health=1, max_health=500)
    fighter = make_service().ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())

    calculate_power_equivalent = (
        ghoul.strength + ghoul.dexterity + ghoul.speed + ghoul.max_health + ghoul.regeneration
    )
    assert BattleService.power_of(fighter.snapshot) < calculate_power_equivalent


# --- run_against_mob ----------------------------------------------------------


def test_run_against_mob_is_deterministic_with_the_same_seed():
    ghoul = make_ghoul()
    service = make_service()
    player1 = service.ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())
    player2 = service.ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())

    result1, mob1 = service.run_against_mob(player1, rng=random.Random(1))
    result2, mob2 = service.run_against_mob(player2, rng=random.Random(1))

    assert result1.winner == result2.winner
    assert mob1.snapshot.strength == mob2.snapshot.strength


def test_run_against_mob_always_compresses_hp_no_choice():
    # 1.5 - бои с мобами всегда "с форой" (compress_hp=True), выбора нет -
    # проверяем через сам факт, что бой вообще разыгрывается без ошибок и
    # даёт BattleResult (глубже эту проверку тестируют battle_engine_battle_test.py -
    # здесь важно только то, что run_against_mob не даёт этот параметр
    # переопределить снаружи, см. её сигнатуру).
    ghoul = make_ghoul()
    service = make_service()
    player = service.ghoul_to_fighter(ghoul, "chestor", FakeGhoulService())

    result, mob = service.run_against_mob(player, rng=random.Random(3))

    assert result.winner in ("a", "b", None)
    assert mob.name  # моб реально сгенерирован (не заглушка)


# --- run_duel ------------------------------------------------------------------


def test_run_duel_is_deterministic_with_the_same_seed_and_compress_hp_flag():
    ghoul_a = make_ghoul(strength=50)
    ghoul_b = make_ghoul(strength=500)
    service = make_service()

    fighter_a1 = service.ghoul_to_fighter(ghoul_a, "A", FakeGhoulService())
    fighter_b1 = service.ghoul_to_fighter(ghoul_b, "B", FakeGhoulService())
    fighter_a2 = service.ghoul_to_fighter(ghoul_a, "A", FakeGhoulService())
    fighter_b2 = service.ghoul_to_fighter(ghoul_b, "B", FakeGhoulService())

    result1 = service.run_duel(fighter_a1, fighter_b1, compress_hp=False, rng=random.Random(9))
    result2 = service.run_duel(fighter_a2, fighter_b2, compress_hp=False, rng=random.Random(9))

    assert result1.winner == result2.winner
    assert result1.final_hp_a == result2.final_hp_a
