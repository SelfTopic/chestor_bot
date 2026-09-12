import random
from typing import Dict, Optional

from src.bot.game_configs import MOB_CONFIG
from src.bot.services.battle_engine.core import FighterSnapshot, validate_snapshot
from src.bot.services.battle_engine.mob import MobService
from src.bot.types import KaguneType


def make_player_snapshot(
    id: int = 1,
    name: str = "Игрок",
    strength: int = 1000,
    dexterity: int = 1000,
    regeneration: int = 1000,
    speed: int = 1000,
    health: int = 5000,
    max_health: Optional[int] = None,
    hunger: int = 100,
    is_kakuja: bool = False,
    kagune_strength: Optional[Dict[KaguneType, int]] = None,
) -> FighterSnapshot:
    return FighterSnapshot(
        id=id,
        name=name,
        strength=strength,
        dexterity=dexterity,
        regeneration=regeneration,
        speed=speed,
        health=health,
        max_health=max_health,
        hunger=hunger,
        is_kakuja=is_kakuja,
        kagune_strength=kagune_strength or {},
    )


def test_generate_mob_scales_all_stats_by_the_same_common_multiplier():
    # Общий множитель на ВСЕ статы разом, а не по отдельности - иначе моб
    # рассыпался бы на набор несвязанных случайных чисел (см. чат).
    player = make_player_snapshot()
    mob = MobService().generate_mob(player, rng=random.Random(0))

    ratios = [
        mob.strength / player.strength,
        mob.dexterity / player.dexterity,
        mob.regeneration / player.regeneration,
        mob.speed / player.speed,
        mob.health / player.health,
    ]
    # Точное равенство не гарантировано - каждый стат округляется отдельно
    # (round()), поэтому сверяем с допуском на погрешность округления, а не
    # побитовое совпадение.
    assert max(ratios) - min(ratios) < 0.001


def test_generate_mob_multiplier_stays_within_configured_range():
    player = make_player_snapshot()
    rng = random.Random(1)
    for _ in range(500):
        mob = MobService().generate_mob(player, rng=rng)
        ratio = mob.strength / player.strength
        assert MOB_CONFIG.stat_multiplier_min - 0.01 <= ratio <= MOB_CONFIG.stat_multiplier_max + 0.01


def test_generate_mob_uses_vacuum_stats_not_effective():
    # Решено явно (см. чат): моб скейлится от ВАКУУМНЫХ (профильных) статов
    # игрока, а не от эффективных (боевых прямо сейчас). MobService в
    # принципе не принимает EffectiveStats/hunger-тир - только FighterSnapshot,
    # так что при одном и том же снапшоте разница в голоде (который влияет
    # только на EffectiveStats через compute_effective_stats, а не на сам
    # снапшот) вообще не может повлиять на генерацию - тот же снапшот даёт
    # тот же диапазон исходов независимо от hunger.
    full = make_player_snapshot(hunger=100)
    hungry = make_player_snapshot(hunger=0)  # тот же вакуумный strength=1000
    mob_full = MobService().generate_mob(full, rng=random.Random(7))
    mob_hungry = MobService().generate_mob(hungry, rng=random.Random(7))
    assert mob_full.strength == mob_hungry.strength


def test_generate_mob_is_a_clean_snapshot_with_no_modifier_chain_bonuses():
    # hunger=100/is_kakuja=False/kagune_strength={} - цепочка модификаторов
    # превращается в тождество (compute_effective_stats), поэтому итоговые
    # боевые статы моба честно равны тому, что сюда положили.
    player = make_player_snapshot()
    mob = MobService().generate_mob(player, rng=random.Random(0))

    assert mob.hunger == 100
    assert mob.is_kakuja is False
    assert mob.kagune_strength == {}


def test_generate_mob_name_comes_from_the_configured_pool():
    player = make_player_snapshot()
    mob = MobService().generate_mob(player, rng=random.Random(0))
    assert mob.name in MOB_CONFIG.names


def test_generate_mob_is_deterministic_with_the_same_seed():
    player = make_player_snapshot()
    mob1 = MobService().generate_mob(player, rng=random.Random(42))
    mob2 = MobService().generate_mob(player, rng=random.Random(42))
    assert mob1 == mob2


def test_generate_mob_never_produces_an_invalid_snapshot_for_a_low_stat_player():
    # Игрок с очень низкими статами (ранний уровень) + multiplier=0.5 могли
    # бы округлиться в 0 у dexterity/speed/health - validate_snapshot этого
    # не прощает (dexterity/speed строго >0, health строго >0).
    weak_player = make_player_snapshot(strength=1, dexterity=1, regeneration=1, speed=1, health=1)
    rng = random.Random(2)
    for _ in range(200):
        mob = MobService().generate_mob(weak_player, rng=rng)
        validate_snapshot(mob)  # не должно бросать InvalidBattleStatsError


def test_generate_mob_id_is_not_a_real_player_id():
    player = make_player_snapshot(id=12345)
    mob = MobService().generate_mob(player, rng=random.Random(0))
    assert mob.id != player.id


def test_generate_mob_health_scales_from_max_health_not_current_health():
    """Регрессия по живому багу: игрок искусственно поднял себе текущий
    health намного выше max_health (например через /set_stat) - моб всё
    равно должен масштабироваться от вакуумного max_health, а не от
    раздутого текущего HP, иначе игрок мог бы намеренно накрутить себе
    гигантский пул и получать таких же гигантских мобов (или наоборот -
    просевший после боя health не должен занижать моба)."""

    player = make_player_snapshot(health=100, max_health=5)
    rng = random.Random(3)
    for _ in range(200):
        mob = MobService().generate_mob(player, rng=rng)
        # health=100 с множителем 0.5-2.0 дал бы 50-200, max_health=5 - 2-10
        # (округление + пол в 1) - диапазоны не пересекаются, поэтому
        # достаточно и одного прогона, но гоняем несколько для надёжности.
        assert mob.health <= 10


def test_generate_mob_health_still_defaults_to_current_health_when_max_health_not_given():
    # Обратная совместимость - большинство существующих тестов/вызовов не
    # указывают max_health явно, там health==max_health и раньше.
    player = make_player_snapshot(health=1000)
    assert player.max_health == 1000
