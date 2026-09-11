from dataclasses import dataclass, field
from random import randint
from typing import List, Optional


@dataclass
class KaguneConfig:
    base_price: int = 100
    exponent: float = 1.7
    linear_multiplier: int = 50


KAGUNE_CONFIG = KaguneConfig()


@dataclass
class SnapConfig:
    min_award: int = 500
    max_award: int = 1500

    @property
    def award(self) -> int:
        return randint(self.min_award, self.max_award)


SNAP_CONFIG = SnapConfig()


@dataclass
class CoffeeConfig:
    min_award: int = 5000
    max_award: int = 9000

    snap_limit = 100

    @property
    def award(self) -> int:
        return randint(self.min_award, self.max_award)


COFFEE_CONFIG = CoffeeConfig()


@dataclass
class QuizConfig:
    min_award: int = 5000
    max_award: int = 10000

    @property
    def award(self) -> int:
        return randint(self.min_award, self.max_award)


QUIZ_CONFIG = QuizConfig()


@dataclass
class LotteryConfig:
    """Конфиг для команды депнуть"""

    min_bet: int = 100
    max_bet: int = 100000
    colors: Optional[list[str]] = None

    # Коэффициенты выигрыша и шансы для каждого цвета
    # formato: {цвет: (коэффициент, шанс_в_процентах)}
    color_multipliers: Optional[dict] = None

    def __post_init__(self):
        if self.colors is None:
            self.colors = ["красный", "синий", "зелёный", "белый", "жёлтый"]

        if self.color_multipliers is None:
            self.color_multipliers = {
                "красный": (1.8, 28),
                "синий": (2.5, 22),
                "зелёный": (3.0, 20),
                "жёлтый": (5.0, 13),
                "белый": (
                    10.0,
                    10,
                ),
            }

    def get_multiplier(self, color: str) -> float:
        """Получить коэффициент для цвета"""
        return self.color_multipliers.get(color, 2.0)[0]

    def get_chance(self, color: str) -> int:
        """Получить шанс выпадения цвета в процентах"""
        return self.color_multipliers.get(color, 25)[1]


LOTTERY_CONFIG = LotteryConfig()


# Health/max_health намеренно дороже прокачивается ДО потолка, чем остальные
# 4 стата, зато и потолок выше - см. живую симуляцию боевого движка
# (scripts/battle_log_all_kagune.py): честный многораундовый бой получается,
# только когда health в ~2.5x больше боевых статов, а не 1:1. Цена за очко
# снижена в те же 2.5 раза - суммарный CheSton до потолка держится наравне с
# остальными статами (никто не платит за health непропорционально больше).
STAT_CAP_MULTIPLIER = {"max_health": 2.5}


def stat_cap_for_level(level: int, stat_key: str = "") -> int:
    """Потолок upgrade_stat для данного уровня и стата. Вынесено из
    StatUpgradeService, чтобы не дублировать формулу там же, где нужно
    посчитать сдвиг пределов при левел-апе (LevelUpService)."""
    return int(level * 100 * STAT_CAP_MULTIPLIER.get(stat_key, 1.0))


@dataclass
class StatUpgradeConfig:
    price_multiplier: int = 2
    multipliers: tuple = (1, 5, 10)
    # Обратная сторона STAT_CAP_MULTIPLIER - см. комментарий выше.
    stat_price_multiplier: dict = field(default_factory=lambda: {"max_health": 0.4})

    def price(self, cur_stat: int, count: int = 1, stat_key: str = "") -> int:
        base_total = count * 1500
        scaling_total = int(sum((cur_stat + i) ** 1.35 for i in range(count)))
        raw = base_total + scaling_total
        return int(raw * self.stat_price_multiplier.get(stat_key, 1.0))


STAT_UPGRADE_CONFIG = StatUpgradeConfig()

STATS = [
    ("Сила", "strength", "💪"),
    ("Ловкость", "dexterity", "🤸‍♂️"),
    ("Скорость", "speed", "🏃"),
    ("Макс. здоровье", "max_health", "❤️"),
    ("Регенерация", "regeneration", "❣️"),
]


@dataclass
class WordleConfig:
    WORD_LENGTH = 5
    MAX_ATTEMPTS = 6
    min_award = 7000
    max_award = 14000

    @property
    def award(self) -> int:
        return randint(self.min_award, self.max_award)


WORDLE_CONFIG = WordleConfig()


@dataclass
class TransferConfig:
    min_amount: int = 1
    max_amount: int = 100_000
    min_sender_account_age_days: int = 3
    max_received_per_day: int = 10


TRANSFER_CONFIG = TransferConfig()


@dataclass
class PassiveStatsConfig:
    """Параметры ленивого расчёта голода/регенерации, см. BATTLE_DESIGN.md."""

    hunger_full_decay_hours: float = 168.0  # 100% -> 0% за 7 суток на обычном голоде
    kakuja_hunger_decay_multiplier: float = 4.0  # какудже голодает в 4 раза быстрее
    health_regen_per_point_per_hour: float = 1.0  # HP в час за 1 очко эфф. regeneration
    kagune_type_multiplier: float = 1.8  # см. "Множители типов кагуне"
    kakuja_multiplier: float = 3.0  # см. порядок применения множителей


PASSIVE_STATS_CONFIG = PassiveStatsConfig()


@dataclass
class EatHumanConfig:
    """Фаза 3a из BATTLE_DESIGN.md - без риска нападения моба (это 3b, после
    боевого движка). Кулдаун (1 сутки) живёт в таблице cooldowns, см.
    migrations/versions/*_insert_new_cooldown_type_eat_human.py."""

    min_hunger_restore: int = 5
    max_hunger_restore: int = 25

    @property
    def hunger_restore(self) -> int:
        return randint(self.min_hunger_restore, self.max_hunger_restore)


EAT_HUMAN_CONFIG = EatHumanConfig()


@dataclass
class LevelUpConfig:
    """Награда за левел-ап, см. LevelUpService. Диапазоны масштабируются
    множителем на НОВЫЙ (уже достигнутый) уровень - на 2м уровне это
    2000-20000 CheSton и 10-40 RC."""

    cheston_min_per_level: int = 1000
    cheston_max_per_level: int = 10000
    rc_min_per_level: int = 5
    rc_max_per_level: int = 20

    def cheston_reward(self, new_level: int) -> int:
        return randint(
            self.cheston_min_per_level * new_level, self.cheston_max_per_level * new_level
        )

    def rc_reward(self, new_level: int) -> int:
        return randint(
            self.rc_min_per_level * new_level, self.rc_max_per_level * new_level
        )


LEVEL_UP_CONFIG = LevelUpConfig()


@dataclass
class BattleConfig:
    """Параметры раундового боевого движка, см. BATTLE_ENGINE.md (часть 2,
    особенно 2.4c). Сама структура формул решена и зафиксирована - здесь
    только числа, часть из которых ещё не сбалансирована (max_rounds в
    первую очередь) и ждёт прогона части 6 (симуляция тысяч боёв)."""

    # Раунды - просто разумный дефолт, не проверен симуляцией.
    max_rounds: int = 30

    # 2.4c: кагуне-защита от физической атаки - неизвестна сила вложенного
    # удара, берём случайность вместо неё.
    physical_block_min: float = 45.0
    physical_block_max: float = 75.0

    # 2.4c: "скромный" блок - кагуне-против-кагуне и физика-против-физики
    # при неотрицательном перевесе защищающегося (удар всё равно приходится
    # по ещё живой части тела/кагуне).
    modest_block_min: float = 10.0
    modest_block_max: float = 20.0

    # 2.4c шаг 2 - гейт "успел ли защищающийся поднять кагуне": при равных
    # dexterity+speed шанс ровно половина.
    kagune_gate_base_percent: float = 50.0

    # Тип атаки (физика/кагуне) - НЕ честная монетка 50/50 (см. историю в
    # чате): первый удар бойца за весь бой гарантированно физический,
    # дальше шанс физической атаки падает на этот процент за КАЖДЫЙ
    # реально нанесённый физический удар (кагуне-удар счётчик не двигает).
    # При decay=10 после 10 физических ударов боец бьёт только кагуне.
    # Будущий навык "мастерство использования кагуне" будет увеличивать
    # именно это значение (не решено, не реализовано).
    physical_attack_decay_percent: float = 10.0

    # 2.4c - неизвестна точность одного удара, берём случайность.
    damage_variance_min: float = 0.9
    damage_variance_max: float = 1.1

    # Бонусный удар от speed (FastAttack) - НЕ полной силы, см. лор в
    # scripts/damage_calculate.py ("атакует чаще МЕЛКИМИ однообразными
    # атаками"). Раньше FastAttack наносил столько же, сколько обычная
    # атака - чистый вклад в speed позволял сносить 3-4 полных удара за
    # раунд 1, что и не соответствовало лору, и было слишком сильно.
    # Диапазон ниже И не центрирован на 1.0, специально смещён вниз.
    fast_attack_damage_variance_min: float = 0.5
    fast_attack_damage_variance_max: float = 0.8

    # Регенерация В БОЮ (обнаружено задним числом - regeneration шёл через
    # полную цепочку модификаторов, но нигде не использовался). Критический
    # порог - % от стартового HP этого боя (см. EffectiveStats.health, не
    # вакуумный max_health). Первое пересечение порога - гарантированный
    # прок, второе - вероятностный (та же формула, что у лишнего удара от
    # speed, см. extra_hit_percent), и ТОЛЬКО ОДИН РАЗ за весь бой -
    # иначе гуль с хорошей регенерацией застревал бы в бою бесконечно.
    # Было 10.0 - в логах регенерация срабатывала слишком редко (см. чат),
    # подняли до 20.0, чтобы критическая зона наступала раньше.
    critical_health_percent: float = 20.0
    regen_heal_variance_min: float = 0.9
    regen_heal_variance_max: float = 1.1

    # 2.6 UX - при одновременном обоюдном нокауте (оба -> 0 HP в одном
    # раунде) реальное правило тай-брейка (кто имел больше HP до
    # последнего обмена) невидимо для игрока - "0 против 0" читается как
    # необъяснённая монетка. Победитель показывается с этим HP вместо 0 -
    # тот же принцип, что и у проигравшего после ВСЕГО боя (3.1 в
    # BATTLE_ENGINE.md, "не 0, а 1 HP").
    mutual_ko_winner_hp: float = 1.0

    # "Кривая перевеса силы" - без этого множителя любое стабильное
    # преимущество в статах (даже 1.1x) почти гарантированно выигрывало за
    # ~7-10 раундов (закон больших чисел: накопленный урон растёт как N,
    # шум - только как sqrt(N)). Решали методом "от обратного" (см. чат):
    # задали целевые точки кривой (2x перевес -> 75% побед, симметрично
    # 0.5x -> 25%, а не 99.9-100%/0%) и бисекцией по scripts/ подобрали
    # экспонент, при котором фактическая симулированная кривая ложится на
    # эти точки (0.03 даёт 2x -> ~73%, 0.5x -> ~26%, очень близко к цели).
    #
    # Применяется через compress_stat_advantage(own, other) - own сжимается
    # К other, только если own>other ("твоё преимущество над ЭТИМ
    # конкретным соперником", а не абстрактная величина) - раньше формула
    # сжимала симметрично с обеих сторон и это ПЕРЕВОРАЧИВАЛО соотношение
    # при большом разрыве (см. историю бага в чате). Используется в
    # raw_damage/raw_fast_attack_damage (сила удара),
    # Fighter.apply_heal (сила хила) и Battle._compress_hp_pools (сам
    # HP-пул - единственный стат, который иначе вообще не проходит ни
    # через одну формулу сравнения). dodge_chance/kagune_gate_chance/
    # extra_hit_percent/regen_proc_chance используют "сырой" _compress_ratio
    # напрямую - они уже были устроены как честное сравнение двух сторон,
    # без нужды в explicit weaker-anchor. При own==other сжатие не меняет
    # ничего (мирные зеркальные бои остаются как были откалиброваны раньше).
    # exponent=1.0 вернул бы старое (не сжатое) поведение, exponent=0.0
    # полностью нейтрализует ЛЮБОЙ перевес статов (проверено симуляцией -
    # даёт ровно 50% на всех ratio).
    stat_sensitivity_exponent: float = 0.03


BATTLE_CONFIG = BattleConfig()


@dataclass
class MobConfig:
    """Параметры генерации моба для "боя с мобом" (BATTLE_DESIGN.md,
    BATTLE_ENGINE.md 1.1) - см. MobService. Статы моба - случайный общий
    множитель от ВАКУУМНЫХ (профильных) статов игрока, а не эффективных
    (боевых прямо сейчас) - решено автором явно: голодный/не в кагуне
    игрок реально встречает моба относительно опаснее, чем по профилю -
    стимул не запускать голод, не баг."""

    stat_multiplier_min: float = 0.5
    stat_multiplier_max: float = 2.0

    # Чисто флейвор - имя моба в логе боя, ни на что не влияет.
    names: List[str] = field(
        default_factory=lambda: [
            "Одичавший гуль",
            "Голодный гуль-бродяга",
            "Безумный гуль",
            "Гуль-падальщик",
            "Раненый гуль-изгой",
            "Гуль без имени",
        ]
    )


MOB_CONFIG = MobConfig()
