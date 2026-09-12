"""Генератор моба для "боя с мобом" (BATTLE_DESIGN.md, BATTLE_ENGINE.md
1.1) - живёт на уровне `battle_engine/`, а не `core/`: формально это
чистая функция без БД (как и text_generator.py), но по роли ближе к
"кому вообще драться" (оркестрация контента), а не к "атомам боя"
(уклонение/урон/защита), которым посвящён `core/`.

Возвращает `FighterSnapshot` НАПРЯМУЮ, без промежуточного типа `Mob` и
без отдельного адаптера - `FighterSnapshot` уже покрывает всё, что нужно
базовому мобу (имя + 5 статов + голод/кагуне/какудж), адаптировать
нечего (см. чат). Рейд-боссы с персистентным общим HP на много игроков -
СТРУКТУРНО другая задача (ломает допущение "Battle.run() разрешает бой
целиком за один вызов"), MobService её не решает и о ней не знает -
см. открытый пункт в BATTLE_DESIGN.md."""

from __future__ import annotations

import random

from ...game_configs import MOB_CONFIG
from .core import FighterSnapshot

_default_rng = random.Random()

# validate_snapshot (core/fighter.py) требует dexterity>0 и speed>0 строго -
# при очень низком статe игрока и multiplier=0.5 round() мог бы дать 0
# (например dexterity=1 -> 0.5 -> round -> 0) и уронить бой ещё до первого
# раунда. Пол в 1 - минимально допустимое значение, не игровой баланс.
_MIN_POSITIVE_STAT = 1


class MobService:
    """`generate_mob` - единственный публичный метод, детерминирован через
    `rng` (как и весь остальной боевой движок - никогда не читает глобальный
    `random`, см. Battle/Fighter)."""

    def generate_mob(
        self, player_snapshot: FighterSnapshot, rng: random.Random = _default_rng
    ) -> FighterSnapshot:
        """Статы моба - ОБЩИЙ случайный множитель (один на все 5 статов,
        не по отдельности на каждый - иначе моб рассыпался бы на набор
        несвязанных случайных чисел вместо цельного "плюс-минус такой же
        по силе противника") от ВАКУУМНЫХ статов `player_snapshot` - см.
        MOB_CONFIG.

        Здоровье - от `player_snapshot.max_health` (вакуумный потолок), а
        НЕ от `player_snapshot.health` (текущее, боевое) - иначе игрок с
        просевшим/искусственно раздутым текущим HP получал бы моба той же
        степени просевшего/раздутого, хотя моб должен зависеть только от
        вакуумной "мощности" игрока (найдено как баг, см. чат)."""

        multiplier = rng.uniform(MOB_CONFIG.stat_multiplier_min, MOB_CONFIG.stat_multiplier_max)
        vacuum_health = (
            player_snapshot.max_health
            if player_snapshot.max_health is not None
            else player_snapshot.health
        )

        return FighterSnapshot(
            id=-1,  # не персистентная сущность - не из БД, id-заглушка
            name=rng.choice(MOB_CONFIG.names),
            strength=max(0, round(player_snapshot.strength * multiplier)),
            dexterity=max(_MIN_POSITIVE_STAT, round(player_snapshot.dexterity * multiplier)),
            regeneration=max(0, round(player_snapshot.regeneration * multiplier)),
            speed=max(_MIN_POSITIVE_STAT, round(player_snapshot.speed * multiplier)),
            health=max(_MIN_POSITIVE_STAT, round(vacuum_health * multiplier)),
            hunger=100,  # "чистый" снапшот - цепочка модификаторов = тождество
            is_kakuja=False,
            kagune_strength={},
        )


__all__ = ["MobService"]
