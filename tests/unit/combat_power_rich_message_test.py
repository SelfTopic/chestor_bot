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
    его ожидает (та же проверка, что и у профиля гуля)."""

    ghoul = _make_ghoul()
    user = SimpleNamespace(full_name="Test User")

    message = build_combat_power_rich_message(
        user, ghoul, FakeGhoulService(), _make_battle_service()
    )

    assert isinstance(message, InputRichMessage)
    assert message.blocks
    dumped = message.model_dump_json(exclude_none=True)
    assert '"type":"heading"' in dumped


def test_build_combat_power_rich_message_health_column_uses_max_health_not_current():
    # health=50 (текущее, раненое) vs max_health=100 (вакуумный потолок,
    # "паспортное" значение) - вакуумная колонка обязана показывать именно
    # max_health (см. BATTLE_ENGINE.md 4.2/1.3), не текущее health.
    ghoul = _make_ghoul(health=50, max_health=100)
    user = SimpleNamespace(full_name="Test User")

    message = build_combat_power_rich_message(
        user, ghoul, FakeGhoulService(), _make_battle_service()
    )
    dumped = message.model_dump_json(exclude_none=True)

    # При hunger=80 (тождественная цепочка) эффективное здоровье = текущему.
    assert "Здоровье: 100 → 50.0" in dumped


def test_build_combat_power_rich_message_effective_power_reflects_hunger():
    ghoul = _make_ghoul(hunger=0)  # "смертельный голод" - падающие статы просажены
    user = SimpleNamespace(full_name="Test User")

    message = build_combat_power_rich_message(
        user, ghoul, FakeGhoulService(), _make_battle_service()
    )
    dumped = message.model_dump_json(exclude_none=True)

    # Вакуумная мощь (calculate_power) не зависит от голода, эффективная -
    # зависит - числа "до" и "после" стрелки обязаны различаться.
    assert "Итого: 500 →" in dumped
    assert "Итого: 500 → 500.0" not in dumped
