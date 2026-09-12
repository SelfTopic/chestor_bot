from types import SimpleNamespace

from aiogram.types import InputRichMessage

from src.bot.routers.ghoul_routers.combat_power import build_combat_power_rich_message
from src.bot.services.battle_engine.battle_service import BattleService
from src.bot.services.battle_engine.mob import MobService
from src.bot.types import KaguneType
from src.database.models import Ghoul


class FakeGhoulService:
    """Минимальный дублёр GhoulService - тот же приём, что в
    race_profile_rich_message_test.py, плюс два метода, нужных именно
    build_combat_power_rich_message."""

    def owned_kagune_types(self, ghoul: Ghoul):
        return [
            kt for kt in KaguneType if getattr(ghoul, kt.value["strength_column"]) is not None
        ]

    def get_kagune_strength(self, ghoul: Ghoul, kagune_type: KaguneType):
        return getattr(ghoul, kagune_type.value["strength_column"])

    def total_kagune_strength(self, ghoul: Ghoul) -> int:
        return sum(
            getattr(ghoul, kt.value["strength_column"]) or 0 for kt in KaguneType
        )

    def calculate_power(self, ghoul: Ghoul) -> int:
        return (
            ghoul.strength
            + ghoul.dexterity
            + ghoul.speed
            + ghoul.max_health
            + ghoul.regeneration
            + self.total_kagune_strength(ghoul)
        )

    def get_danger_rank(self, power: int) -> str:
        return "F" if power < 500 else "D"


def _make_ghoul(**overrides) -> Ghoul:
    defaults = dict(
        telegram_id=1,
        strength=100,
        dexterity=100,
        speed=100,
        regeneration=100,
        health=50,
        max_health=100,
        hunger=80,  # "не голоден" (75-100) - цепочка модификаторов = тождество
        is_kakuja=False,
        kagune_strength_ukaku=None,
        kagune_strength_koukaku=None,
        kagune_strength_rinkaku=None,
        kagune_strength_bikaku=None,
    )
    defaults.update(overrides)
    return Ghoul(**defaults)


def _make_battle_service() -> BattleService:
    return BattleService(mob_service=MobService())


def test_build_combat_power_rich_message_returns_valid_input_rich_message():
    """Единственное, что можно проверить без живого бота - что дерево
    блоков реально сериализуется в JSON в том виде, в котором Bot API
    его ожидает (та же проверка, что и у профиля гуля), и что там
    действительно две таблицы (см. BATTLE_ENGINE.md 8.4 - "фиктивная" и
    "боевая")."""

    ghoul = _make_ghoul()
    user = SimpleNamespace(full_name="Test User")
    fake_service = FakeGhoulService()

    message = build_combat_power_rich_message(
        user, ghoul, fake_service.get_danger_rank(fake_service.calculate_power(ghoul)),
        fake_service, _make_battle_service(),
    )

    assert isinstance(message, InputRichMessage)
    assert message.blocks
    dumped = message.model_dump_json(exclude_none=True)
    assert '"type":"heading"' in dumped
    assert dumped.count('"type":"table"') == 2


def test_build_combat_power_rich_message_health_column_uses_max_health_not_current():
    # health=50 (текущее, раненое) vs max_health=100 (вакуумный потолок,
    # "паспортное" значение) - вакуумная таблица обязана показывать именно
    # max_health (см. BATTLE_ENGINE.md 4.2/1.3), боевая - текущее (базовое
    # значение цепочки), не max_health.
    ghoul = _make_ghoul(health=50, max_health=100)
    user = SimpleNamespace(full_name="Test User")
    fake_service = FakeGhoulService()

    message = build_combat_power_rich_message(
        user, ghoul, "F", fake_service, _make_battle_service()
    )
    dumped = message.model_dump_json(exclude_none=True)

    # Вакуумная таблица: "Здоровье" -> "100".
    assert '"text":"Здоровье"' in dumped
    assert '"text":"100"' in dumped
    # Боевая таблица: базовое значение для здоровья = текущее (50), при
    # hunger=80 (тождественная цепочка) финальное эффективное тоже 50.0.
    assert '"text":"50"' in dumped
    assert '"text":"50.0"' in dumped


def test_build_combat_power_rich_message_effective_power_reflects_hunger():
    ghoul = _make_ghoul(hunger=0)  # "смертельный голод" - падающие статы просажены
    user = SimpleNamespace(full_name="Test User")
    fake_service = FakeGhoulService()

    message = build_combat_power_rich_message(
        user, ghoul, "F", fake_service, _make_battle_service()
    )
    dumped = message.model_dump_json(exclude_none=True)

    # Вакуумная мощь (Итого в фиктивной таблице) не зависит от голода (500).
    # Эффективная (Итого в боевой таблице, последний столбец) - зависит:
    # hunger=0 -> falling=0.1/rising=0.5, health=50 (текущее, из дефолта):
    # 100*0.5 + 100*0.1 + 100*0.1 + 50*0.1 + 100*0.1 + 0 = 85.0.
    assert '"text":"500"' in dumped
    assert '"text":"85.0"' in dumped
