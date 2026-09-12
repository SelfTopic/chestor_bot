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
from typing import TYPE_CHECKING, Dict, List, Optional, Protocol, Tuple

from ...types import KaguneType
from .core import Battle, BattleResult, Fighter, FighterSnapshot
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
            health=ghoul.max_health,  # полный боевой пул на старт боя, не текущее (возможно урезанное) HP
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


__all__ = ["BattleService"]
