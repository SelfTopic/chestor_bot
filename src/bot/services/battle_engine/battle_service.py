"""Собирает `Fighter` из "внешних" типов (`Ghoul` - БД, `MobService` -
генератор мобов) и разыгрывает бой - недостающее звено между "у нас есть
`Ghoul` из БД" и "`Battle` умеет работать только с `Fighter`" (см. чат).

Живёт на уровне `battle_engine/` (не `core/`) по той же причине, что
`MobService`/`BattleTextGenerator` - формально не трогает БД напрямую
(только читает уже загруженные объекты), но по роли явно "мост между
игровым миром и движком", а не "атом боя".

Не решает ЗА вызывающего: `compress_hp` ("всерьёз"/"дать фору", 1.5)
остаётся параметром для дуэлей - решение о его значении принимает внешний
слой (ЛС + таймер, ещё не написан). Для боёв с мобами это НЕ параметр
вообще - 1.5 явно решил "бои с мобами - всегда compress_hp=True, выбора
нет", поэтому `run_against_mob` не даёт его переопределить."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, List, Optional, Protocol, Tuple

from ...exceptions import (
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
)
from ...game_configs import BATTLE_CONFIG
from ...types import KaguneType
from .core import Battle, BattleResult, EffectiveStats, Fighter, FighterSnapshot
from .mob import MobService

if TYPE_CHECKING:
    from src.database.models import Ghoul

_default_rng = random.Random()


class _KaguneLookup(Protocol):
    """Только то подмножество GhoulService, которое реально нужно
    ghoul_to_fighter - структурный тип (Protocol), а не конкретный класс,
    чтобы тесты могли подставить лёгкий дублёр без БД (тот же паттерн, что
    уже был в mob_fight_preview.py до этого рефакторинга и в
    race_profile_rich_message_test.py)."""

    def owned_kagune_types(self, ghoul: "Ghoul") -> List[KaguneType]: ...
    def get_kagune_strength(self, ghoul: "Ghoul", kagune_type: KaguneType) -> Optional[int]: ...


class BattleService:
    def __init__(self, mob_service: MobService) -> None:
        self._mob_service = mob_service

    async def validate_ghoul(
        self,
        ghoul: "Ghoul",
        has_pending_confirmation: Optional[Callable[["Ghoul"], Awaitable[bool]]] = None,
    ) -> None:
        """Бросает `BattleError` (см. подклассы в `exceptions/battle.py`),
        если ЭТОТ гуль прямо сейчас не может вступить в бой - вызывать
        ПЕРЕД любой попыткой построить `Fighter`/`Battle` (не тратить время
        на сборку боя, который всё равно нельзя провести).

        Для дуэли вызвать на ОБЕИХ сторон (см. `validate_duel`) - для боя с
        мобом достаточно вызвать один раз на игрока, у моба нет ни
        `is_dead`, ни ожидающих подтверждения вызовов.

        `has_pending_confirmation` - опциональный АСИНХРОННЫЙ колбэк "есть
        ли у этого гуля неподтверждённый вызов на бой?" (см.
        `FighterHasPendingBattleError`) - асинхронный, потому что реальная
        проверка идёт в БД (`BattleRecordService.is_busy`, см.
        `active_battles` - тот самый лок, который закрывает эксплойт
        "твинк-дуэль + бой с мобом одновременно"). Вызывающий код передаёт
        сюда что-то вроде `lambda g: battle_record_service.is_busy(g.telegram_id)`.
        Параметр опционален (по умолчанию проверка пропускается) - для
        боя с мобом-превью (`mob_fight_preview.py`) она не нужна вовсе,
        он не персистентен и лок не занимает."""

        if ghoul.is_dead:
            raise FighterIsDeadError(ghoul.id)

        if ghoul.health < BATTLE_CONFIG.min_health_to_fight:
            raise FighterNotCombatReadyError(
                ghoul.id, ghoul.health, BATTLE_CONFIG.min_health_to_fight
            )

        if has_pending_confirmation is not None and await has_pending_confirmation(ghoul):
            raise FighterHasPendingBattleError(ghoul.id)

    async def validate_duel(
        self,
        ghoul_a: "Ghoul",
        ghoul_b: "Ghoul",
        has_pending_confirmation: Optional[Callable[["Ghoul"], Awaitable[bool]]] = None,
    ) -> None:
        """Удобный шорткат для PvP - `validate_ghoul` на обе стороны.
        Останавливается на первой же провалившейся проверке (не пытается
        собрать сразу все причины отказа - вызывающему коду для
        сообщения игроку достаточно одной)."""

        await self.validate_ghoul(ghoul_a, has_pending_confirmation)
        await self.validate_ghoul(ghoul_b, has_pending_confirmation)

    def ghoul_to_fighter(self, ghoul: "Ghoul", name: str, ghoul_service: _KaguneLookup) -> Fighter:
        kagune_strength: Dict[KaguneType, int] = {}
        for kagune_type in ghoul_service.owned_kagune_types(ghoul):
            strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
            # owned_kagune_types уже отфильтровал типы с None (см. GhoulService) -
            # assert только чтобы pyright не видел здесь Optional[int].
            assert strength is not None
            kagune_strength[kagune_type] = strength

        snapshot = FighterSnapshot(
            id=ghoul.id,
            name=name,
            strength=ghoul.strength,
            dexterity=ghoul.dexterity,
            regeneration=ghoul.regeneration,
            speed=ghoul.speed,
            # ТЕКУЩЕЕ health, не max_health - иначе гуль с 1 HP (например,
            # только что проигравший бой, см. 3.1 в BATTLE_ENGINE.md)
            # начинал бы каждый следующий бой при полном пуле, полностью
            # игнорируя пассивную регенерацию здоровья (см. чат) - весь
            # смысл health как медленно восстанавливающегося ресурса между
            # боями был бы потерян. materialize_passive_stats (вызывается
            # внутри GhoulService.get) досчитывает health на текущий
            # момент ДО того, как ghoul попадёт сюда - значение уже честное.
            health=ghoul.health,
            # Вакуумный потолок из профиля - НЕ участвует в самом бою
            # (движок работает от текущего health выше), но нужен
            # MobService.generate_mob, чтобы масштабировать моба от
            # вакуумной "мощности" игрока, а не от того, сколько у него
            # HP прямо сейчас (иначе искусственно раздутый/просевший
            # health давал бы такого же противоестественного моба - см.
            # чат, найдено как баг).
            max_health=ghoul.max_health,
            hunger=ghoul.hunger,
            is_kakuja=ghoul.is_kakuja,
            kagune_strength=kagune_strength,
        )
        return Fighter(snapshot)

    def run_against_mob(
        self, player: Fighter, rng: random.Random = _default_rng
    ) -> Tuple[BattleResult, Fighter]:
        """Генерирует моба относительно `player` (вакуумные статы, см.
        MobService) и разыгрывает бой ЦЕЛИКОМ (compress_hp=True всегда -
        см. докстринг модуля, для мобов выбора "всерьёз/фора" нет).
        Возвращает и `BattleResult`, и `Fighter` моба - вызывающему коду
        (роутеру) он тоже нужен для BattleTextGenerator (имя/статы)."""

        mob_snapshot = self._mob_service.generate_mob(player.snapshot, rng=rng)
        mob_fighter = Fighter(mob_snapshot)
        result = Battle(player, mob_fighter, compress_hp=True).run(rng=rng)
        return result, mob_fighter

    def run_duel(
        self,
        fighter_a: Fighter,
        fighter_b: Fighter,
        compress_hp: bool = True,
        rng: random.Random = _default_rng,
    ) -> BattleResult:
        """PvP - оба Fighter уже собраны вызывающим (ghoul_to_fighter на
        обе стороны). compress_hp - параметр, а не решение этого метода:
        значение выбирает внешний слой (1.5), здесь просто плюмбинг."""

        return Battle(fighter_a, fighter_b, compress_hp=compress_hp).run(rng=rng)

    @staticmethod
    def power_of(snapshot: FighterSnapshot) -> int:
        """То же слагаемое, что GhoulService.calculate_power, но по
        FighterSnapshot - работает для ОБЕИХ сторон одинаково (для игрока
        даёт то же число, что calculate_power(ghoul), потому что
        ghoul_to_fighter зеркалит те же поля 1:1; для моба считать
        отдельно больше не от кого - строки Ghoul у него нет)."""

        return (
            snapshot.strength
            + snapshot.dexterity
            + snapshot.speed
            + snapshot.health
            + snapshot.regeneration
            + snapshot.total_kagune_strength
        )

    @staticmethod
    def effective_power_of(stats: EffectiveStats) -> float:
        """Та же сумма, что `power_of`, но по `EffectiveStats` (ПОСЛЕ
        цепочки модификаторов голод → тип кагуне → какудж) - для команды
        "боевая мощь" (BATTLE_ENGINE.md 8.4), чтобы показать игроку не
        только вакуумную мощь (`power_of`/`calculate_power`), но и то,
        сколько из неё реально мобилизуется на бой ПРЯМО СЕЙЧАС."""

        return (
            stats.strength
            + stats.dexterity
            + stats.speed
            + stats.health
            + stats.regeneration
            + stats.kagune_strength
        )

    @staticmethod
    def resolve_post_battle_health(
        base_health_before: int, effective_max: float, final_hp: float
    ) -> int:
        """Переводит HP бойца ПОСЛЕ боя обратно на вакуумный масштаб
        `Ghoul.health` - `Fighter.stats.health`/`BattleResult.final_hp_*`
        живут на "эффективном" масштабе (после голода/типа кагуне/какуджи
        И после compress_hp-сжатия, см. `Battle._compress_hp_pools`),
        который отличается от того, что хранится в БД.

        `base_health_before` - `ghoul.health` ДО боя (то, что ушло в
        `ghoul_to_fighter`); `effective_max`/`final_hp` - `EffectiveStats.
        health`/`BattleResult.final_hp_*` ОДНОЙ и той же стороны.

        0 эффективного HP (естественный проигрыш или настоящая ничья, см.
        BATTLE_ENGINE.md 2.6) флорится в 1 - "бой сам по себе не убивает"
        (3.1) это игровое правило, а не физика, поэтому не выводится из
        пропорции. Иначе - переносим ДОЛЮ оставшегося HP на вакуумный
        масштаб (не на max_health - та же причина, что и в
        ghoul_to_fighter: гуль мог войти в бой уже не при полном
        здоровье)."""

        if final_hp <= 0:
            return 1

        fraction = final_hp / effective_max if effective_max > 0 else 0.0
        return max(1, round(base_health_before * fraction))


__all__ = ["BattleService"]
