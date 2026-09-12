from types import SimpleNamespace

from aiogram.types import InputRichMessage

from src.bot.routers.common.race_profile_router import build_ghoul_profile_rich_message
from src.bot.types import KaguneType
from src.database.models import Ghoul


class FakeGhoulService:
    """Минимальный дублёр GhoulService - тесту нужны только эти два метода,
    без БД."""

    def owned_kagune_types(self, ghoul: Ghoul):
        return [
            kt
            for kt in KaguneType
            if getattr(ghoul, kt.value["strength_column"]) is not None
        ]

    def get_kagune_strength(self, ghoul: Ghoul, kagune_type: KaguneType):
        return getattr(ghoul, kagune_type.value["strength_column"])


def _make_ghoul(**overrides) -> Ghoul:
    defaults = dict(
        telegram_id=1,
        level=3,
        level_progress=42.5,
        hunger=63,
        rc_money=500,
        kagune_type_bit=KaguneType.UKAKU.value["bit"] | KaguneType.BIKAKU.value["bit"],
        kagune_strength_ukaku=18,
        kagune_strength_koukaku=None,
        kagune_strength_rinkaku=None,
        kagune_strength_bikaku=10,
        snap_count=100,
        coffee_count=3,
        eat_humans=1,
        eat_ghouls=0,
        strength=1,
        speed=1,
        dexterity=1,
        health=5,
        max_health=5,
        regeneration=1,
        is_kakuja=False,
        deaths=0,
    )
    defaults.update(overrides)
    return Ghoul(**defaults)


def test_build_ghoul_profile_rich_message_returns_valid_input_rich_message():
    """Главная проверка: pydantic обязан принять всё дерево блоков без
    ValidationError - это единственное, что можно проверить без живого
    бота, но зато проверяет ту же схему, что реально уходит в Bot API."""

    ghoul = _make_ghoul()
    user = SimpleNamespace(full_name="Test User")

    message = build_ghoul_profile_rich_message(
        user, ghoul, FakeGhoulService(), danger_rank="B", power=123, wins=7, losses=3, total_battles=10
    )

    assert isinstance(message, InputRichMessage)
    assert message.blocks
    # Не должно падать - подтверждает, что дерево реально сериализуемо в JSON
    # в том виде, в котором Bot API его ожидает (discriminated union по "type").
    dumped = message.model_dump_json(exclude_none=True)
    assert '"type":"heading"' in dumped
    assert '"type":"details"' in dumped


def test_build_ghoul_profile_rich_message_lists_only_owned_kagune_types():
    ghoul = _make_ghoul()  # ukaku + bikaku открыты, koukaku/rinkaku - нет
    user = SimpleNamespace(full_name="Test User")

    message = build_ghoul_profile_rich_message(
        user, ghoul, FakeGhoulService(), danger_rank="B", power=123, wins=7, losses=3, total_battles=10
    )

    dumped = message.model_dump_json(exclude_none=True)
    assert "Укаку - 18" in dumped
    assert "Бикаку - 10" in dumped
    assert "Коукаку" not in dumped
    assert "Ринкаку" not in dumped


def test_build_ghoul_profile_rich_message_includes_deaths_and_kakuja():
    ghoul = _make_ghoul(deaths=5, is_kakuja=True)
    user = SimpleNamespace(full_name="Test User")

    message = build_ghoul_profile_rich_message(
        user, ghoul, FakeGhoulService(), danger_rank="B", power=123, wins=7, losses=3, total_battles=10
    )

    dumped = message.model_dump_json(exclude_none=True)
    assert "Смертей: 5" in dumped
    assert "Какуджа: Есть" in dumped


def test_build_ghoul_profile_rich_message_includes_battle_counters():
    ghoul = _make_ghoul()
    user = SimpleNamespace(full_name="Test User")

    message = build_ghoul_profile_rich_message(
        user, ghoul, FakeGhoulService(), danger_rank="B", power=123, wins=7, losses=3, total_battles=10
    )

    dumped = message.model_dump_json(exclude_none=True)
    assert "Всего боёв: 10 (7 побед / 3 поражений)" in dumped
