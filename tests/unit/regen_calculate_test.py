from datetime import timedelta

import pytest

from src.bot.types import KaguneType
from src.bot.utils import (
    apply_hunger_restore,
    compute_health,
    compute_hunger,
    get_hunger_tier,
    hours_until_full_health,
    hours_until_hunger_threshold,
    hours_until_starved,
    next_hunger_threshold,
)
from src.bot.utils.regen_calculate import health_regen_per_hour
from src.bot.utils.time_now import utcnow_naive


def test_hunger_tier_boundaries():
    assert get_hunger_tier(100).name == "не голоден"
    assert get_hunger_tier(75).name == "не голоден"
    assert get_hunger_tier(74).name == "лёгкий голод"
    assert get_hunger_tier(50).name == "лёгкий голод"
    assert get_hunger_tier(49).name == "сильный голод"
    assert get_hunger_tier(25).name == "сильный голод"
    assert get_hunger_tier(24).name == "смертельный голод"
    assert get_hunger_tier(0).name == "смертельный голод"


def test_compute_hunger_no_change_before_a_full_point():
    """Регрессия по классу бага с округлением кулдауна кофе: если прошло
    меньше времени, чем нужно для потери хотя бы 1%, значение и timestamp
    обязаны остаться нетронутыми - иначе дробный остаток теряется при частых
    чтениях и голод может вообще перестать течь."""
    now = utcnow_naive()
    updated_at = now - timedelta(minutes=1)  # << 168ч/100 на один процент

    new_hunger, new_updated_at, would_starve = compute_hunger(
        hunger=100, hunger_updated_at=updated_at, is_kakuja=False, now=now
    )

    assert new_hunger == 100
    assert new_updated_at == updated_at
    assert would_starve is False


def test_compute_hunger_carries_leftover_time_precisely():
    """168 часов - весь голод (100%). Проверяем, что после ровно половины
    этого времени потеряна ровно половина голода, и remainder-время учтено
    (не "прыгнули" в now, что съело бы недостающий остаток)."""
    now = utcnow_naive()
    updated_at = now - timedelta(hours=84)  # ровно половина от 168ч

    new_hunger, new_updated_at, would_starve = compute_hunger(
        hunger=100, hunger_updated_at=updated_at, is_kakuja=False, now=now
    )

    assert new_hunger == 50
    assert new_updated_at == now
    assert would_starve is False


def test_compute_hunger_kakuja_decays_four_times_faster():
    now = utcnow_naive()
    updated_at = now - timedelta(hours=21)  # 168/4 = 42ч на полный голод у какудж

    new_hunger, _, _ = compute_hunger(
        hunger=100, hunger_updated_at=updated_at, is_kakuja=True, now=now
    )

    assert new_hunger == 50


def test_compute_hunger_would_starve_flag_and_clamps_at_zero():
    now = utcnow_naive()
    updated_at = now - timedelta(hours=168 * 10)  # заведомо больше, чем есть голода

    new_hunger, _, would_starve = compute_hunger(
        hunger=5, hunger_updated_at=updated_at, is_kakuja=False, now=now
    )

    assert new_hunger == 0
    assert would_starve is True


def test_compute_health_regens_and_caps_at_max():
    now = utcnow_naive()
    updated_at = now - timedelta(hours=10)

    new_health, new_updated_at = compute_health(
        health=1, health_updated_at=updated_at, max_health=5, hp_per_hour=1.0, now=now
    )

    # 10 часов * 1 HP/ч = 10, но потолок max_health=5
    assert new_health == 5
    # timestamp продвинут только на 4 часа (сколько реально понадобилось,
    # чтобы долечиться с 1 до 5), а не на все прошедшие 10
    assert new_updated_at == updated_at + timedelta(hours=4)


def test_compute_health_no_change_below_one_point():
    now = utcnow_naive()
    updated_at = now - timedelta(minutes=30)

    new_health, new_updated_at = compute_health(
        health=1, health_updated_at=updated_at, max_health=5, hp_per_hour=1.0, now=now
    )

    assert new_health == 1
    assert new_updated_at == updated_at


def test_health_regen_per_hour_uses_hunger_tier_and_kagune_and_kakuja():
    # сыт, нет кагуне-бонуса, не какудж - чистый стат
    base = health_regen_per_hour(
        regeneration=10, hunger=100, kagune_type_bit=0, is_kakuja=False
    )
    assert base == 10.0

    # смертельный голод - падающий стат режется 0.1x
    starving = health_regen_per_hour(
        regeneration=10, hunger=10, kagune_type_bit=0, is_kakuja=False
    )
    assert starving == 1.0

    # Ринкаку даёт 1.8x поверх сытого состояния
    rinkaku = health_regen_per_hour(
        regeneration=10,
        hunger=100,
        kagune_type_bit=KaguneType.RINKAKU.value["bit"],
        is_kakuja=False,
    )
    assert rinkaku == 18.0

    # Укаку регенерацию не трогает (только скорость) - множителя быть не должно
    ukaku = health_regen_per_hour(
        regeneration=10,
        hunger=100,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        is_kakuja=False,
    )
    assert ukaku == 10.0

    # какудж поверх всего - 3x
    kakuja = health_regen_per_hour(
        regeneration=10, hunger=100, kagune_type_bit=0, is_kakuja=True
    )
    assert kakuja == 30.0


def test_hours_until_starved():
    assert hours_until_starved(hunger=50, is_kakuja=False) == 84.0  # половина от 168ч
    assert hours_until_starved(hunger=50, is_kakuja=True) == 21.0  # в 4 раза быстрее
    assert hours_until_starved(hunger=0, is_kakuja=False) == 0.0


def test_hours_until_full_health():
    assert hours_until_full_health(health=5, max_health=5, hp_per_hour=1.0) == 0.0
    assert hours_until_full_health(health=0, max_health=5, hp_per_hour=1.0) == 5.0
    assert hours_until_full_health(health=0, max_health=5, hp_per_hour=0.0) is None


def test_apply_hunger_restore_clamps_at_100():
    assert apply_hunger_restore(hunger=50, restore_percent=25) == 75
    assert apply_hunger_restore(hunger=90, restore_percent=25) == 100


def test_next_hunger_threshold():
    assert next_hunger_threshold(100) == 75
    assert next_hunger_threshold(76) == 75
    assert next_hunger_threshold(75) == 50  # уже на границе - следующий порог ниже
    assert next_hunger_threshold(50) == 25
    assert next_hunger_threshold(25) == 0
    assert next_hunger_threshold(1) == 0
    assert next_hunger_threshold(0) is None
    assert next_hunger_threshold(-5) is None


def test_hours_until_hunger_threshold():
    assert hours_until_hunger_threshold(100, is_kakuja=False, threshold=75) == pytest.approx(
        25 * 168 / 100
    )
    assert hours_until_hunger_threshold(50, is_kakuja=False, threshold=50) == 0.0
    # не может быть отрицательным, даже если голод уже ниже порога
    assert hours_until_hunger_threshold(10, is_kakuja=False, threshold=50) == 0.0
