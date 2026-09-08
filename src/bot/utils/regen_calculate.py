"""
Ленивый расчёт голода и регенерации здоровья, см. BATTLE_DESIGN.md
("Множители голода", "Модель боя: раунды и лог событий").

Ничего здесь не работает "по тику" - нет фонового процесса. Вместо этого
каждая функция принимает последний сохранённый снапшот (значение + время) и
текущее время, и говорит, что должно быть "прямо сейчас".

Важная деталь дисциплины (тот же класс бага, что был с округлением кулдауна
кофе, см. coffee.py): если материализовать (записывать обратно) при КАЖДОМ
чтении, продвигая timestamp сразу до "сейчас", дробный остаток времени,
не набравший целого процента/HP, будет теряться при каждом чтении - и при
достаточно частых чтениях голод/реген могут вообще перестать течь. Поэтому
timestamp снапшота продвигается только на то время, которое реально
"обналичено" в виде целого пункта изменения - остаток всегда переносится
на будущее.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from ..game_configs import PASSIVE_STATS_CONFIG
from ..types import KaguneType

_REGEN_BOOSTING_KAGUNE_BITS = (
    KaguneType.RINKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"]
)


@dataclass(frozen=True)
class HungerTier:
    name: str
    min_hunger: int
    max_hunger: int
    falling_multiplier: float
    rising_multiplier: float


HUNGER_TIERS: tuple[HungerTier, ...] = (
    HungerTier("не голоден", 75, 100, 1.0, 1.0),
    HungerTier("лёгкий голод", 50, 74, 0.9, 1.1),
    HungerTier("сильный голод", 25, 49, 0.6, 1.6),
    HungerTier("смертельный голод", 0, 24, 0.1, 0.5),
)


def get_hunger_tier(hunger: int) -> HungerTier:
    for tier in HUNGER_TIERS:
        if tier.min_hunger <= hunger <= tier.max_hunger:
            return tier
    # hunger < 0 не должен долго существовать (см. триггер смерти), но
    # на всякий случай не даём упасть - берём худший тир.
    return HUNGER_TIERS[-1]


def effective_regeneration(
    regeneration: int, hunger: int, kagune_type_bit: int, is_kakuja: bool
) -> float:
    """regeneration - "падающий" стат: голод бьёт по нему первым, затем тип
    кагуне (Ринкаку/Бикаку), затем какуджа - см. порядок в "Множители голода"
    и "Множители типов кагуне"."""

    tier = get_hunger_tier(hunger)
    value = regeneration * tier.falling_multiplier

    if kagune_type_bit & _REGEN_BOOSTING_KAGUNE_BITS:
        value *= PASSIVE_STATS_CONFIG.kagune_type_multiplier

    if is_kakuja:
        value *= PASSIVE_STATS_CONFIG.kakuja_multiplier

    return value


def hunger_decay_per_hour(is_kakuja: bool) -> float:
    rate = 100.0 / PASSIVE_STATS_CONFIG.hunger_full_decay_hours
    if is_kakuja:
        rate *= PASSIVE_STATS_CONFIG.kakuja_hunger_decay_multiplier
    return rate


def hours_until_hunger_threshold(hunger: int, is_kakuja: bool, threshold: int) -> float:
    """Часов до того, как голод дойдёт (сверху вниз) до threshold."""
    return max(0.0, (hunger - threshold) / hunger_decay_per_hour(is_kakuja))


def hours_until_starved(hunger: int, is_kakuja: bool) -> float:
    """Прогноз "через сколько часов голод дойдёт до 0", если ничего не есть.
    Само по себе смерть не вызывает (см. "Смерть и сброс" в BATTLE_DESIGN.md) -
    только оценка для отображения игроку."""
    return hours_until_hunger_threshold(hunger, is_kakuja, threshold=0)


# Тиры голода дают ровно нужные пороги пуш-уведомлений (75/50/25/0) - те же
# min_hunger значения, что и в HUNGER_TIERS, порядок убывания важен.
HUNGER_NOTIFICATION_THRESHOLDS: tuple[int, ...] = tuple(
    tier.min_hunger for tier in HUNGER_TIERS
)


def next_hunger_threshold(hunger: int) -> int:
    """Следующий порог (75/50/25/0), который голод пересечёт сверху вниз.

    При hunger <= 0 возвращает -1 - не настоящий процент, а "будильник" на
    момент, когда СЛЕДУЮЩАЯ убыль голода уйдёт в минус (см. триггер смерти в
    "Смерть и сброс"). Без этого неактивный игрок, чей голод застрял ровно
    на 0%, никогда бы не умер - никто не читает его гуля, чтобы пересчитать
    голод дальше, а следующего порога для планирования не было бы вообще.

    None не возвращается никогда - только явный вызывающий код (например,
    после реального наступления смерти) должен переставать планировать."""
    for threshold in HUNGER_NOTIFICATION_THRESHOLDS:
        if hunger > threshold:
            return threshold
    return -1


def hours_until_full_health(
    health: int, max_health: int, hp_per_hour: float
) -> Optional[float]:
    """None значит "никогда не долечится при текущей скорости регена" -
    например regeneration=0 (обычно достижимо только через /set_stat)."""
    if health >= max_health:
        return 0.0
    if hp_per_hour <= 0:
        return None
    return (max_health - health) / hp_per_hour


def compute_hunger(
    hunger: int,
    hunger_updated_at: datetime,
    is_kakuja: bool,
    now: datetime,
) -> tuple[int, datetime, bool]:
    """Возвращает (новый_hunger, новый_hunger_updated_at, would_starve).

    would_starve=True значит: непотраченного времени хватило бы, чтобы увести
    голод ниже нуля - по дизайну это триггер смерти (см. "Смерть и сброс").
    Здесь только сигнализируется - вызывающий код пока НЕ обязан на это
    реагировать (смерть/сброс - отдельный, ещё не реализованный шаг)."""

    decay_per_hour = hunger_decay_per_hour(is_kakuja)
    elapsed_hours = max(0.0, (now - hunger_updated_at).total_seconds() / 3600)

    raw_points_lost = int(elapsed_hours * decay_per_hour)
    if raw_points_lost <= 0:
        return hunger, hunger_updated_at, False

    would_starve = raw_points_lost > hunger
    capped_loss = min(raw_points_lost, hunger)

    new_hunger = hunger - capped_loss
    hours_consumed = capped_loss / decay_per_hour
    new_updated_at = hunger_updated_at + timedelta(hours=hours_consumed)

    return new_hunger, new_updated_at, would_starve


def compute_health(
    health: int,
    health_updated_at: datetime,
    max_health: int,
    hp_per_hour: float,
    now: datetime,
) -> tuple[int, datetime]:
    if health >= max_health or hp_per_hour <= 0:
        return health, health_updated_at

    elapsed_hours = max(0.0, (now - health_updated_at).total_seconds() / 3600)
    raw_points_gained = int(elapsed_hours * hp_per_hour)
    if raw_points_gained <= 0:
        return health, health_updated_at

    capped_gain = min(raw_points_gained, max_health - health)
    new_health = health + capped_gain
    hours_consumed = capped_gain / hp_per_hour
    new_updated_at = health_updated_at + timedelta(hours=hours_consumed)

    return new_health, new_updated_at


def apply_hunger_restore(hunger: int, restore_percent: int) -> int:
    """Голод не может уйти выше 100% - клэмп сверху. Случайную величину
    восстановления (5-25%, см. EAT_HUMAN_CONFIG) катает вызывающий код -
    здесь только чистое применение."""
    return min(100, hunger + restore_percent)


def health_regen_per_hour(
    regeneration: int, hunger: int, kagune_type_bit: int, is_kakuja: bool
) -> float:
    effective = effective_regeneration(regeneration, hunger, kagune_type_bit, is_kakuja)
    return effective * PASSIVE_STATS_CONFIG.health_regen_per_point_per_hour
