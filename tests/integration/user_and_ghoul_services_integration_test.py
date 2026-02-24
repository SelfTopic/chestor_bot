import pytest

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.ghoul import GhoulService
from src.bot.services.user import UserService
from src.bot.types import Race


@pytest.fixture
def user_service(session):
    return UserService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
    )


@pytest.fixture
def ghoul_service(session):
    return GhoulService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
    )


# --- Полный цикл регистрации гуля ---


async def test_register_ghoul_sets_race_on_user(user_service, ghoul_service, make_user):
    """После register() у пользователя должен стоять race_bit гуля."""
    await make_user(telegram_id=700_000_001)

    result = await ghoul_service.register(telegram_id=700_000_001)
    assert result.ok is True

    user = await user_service.get(find_by=700_000_001)
    assert user is not None
    assert user.race_bit == Race.GHOUL.value["bit"]


async def test_register_ghoul_creates_kagune(ghoul_service, make_user):
    """Зарегистрированный гуль должен иметь kagune_type_bit."""
    await make_user(telegram_id=700_000_002)
    result = await ghoul_service.register(telegram_id=700_000_002)
    assert result.ghoul is not None
    assert result.ghoul.kagune_type_bit is not None
    assert result.ghoul.kagune_type_bit > 0


async def test_double_register_is_idempotent(ghoul_service, make_user):
    """Повторная регистрация не должна перезаписывать гуля."""
    await make_user(telegram_id=700_000_003)
    first = await ghoul_service.register(telegram_id=700_000_003)
    second = await ghoul_service.register(telegram_id=700_000_003)

    assert first.ok is True
    assert second.ok is False
    assert second.ghoul is None


# --- Баланс и гуль живут независимо ---


async def test_balance_change_does_not_affect_ghoul(
    user_service, ghoul_service, make_user
):
    await make_user(telegram_id=700_000_100)
    await ghoul_service.register(telegram_id=700_000_100)

    await user_service.plus_balance(telegram_id=700_000_100, change_balance=500)

    ghoul = await ghoul_service.get(find_by=700_000_100)
    user = await user_service.get(find_by=700_000_100)

    assert user.balance == 500
    assert ghoul.snap_count == 0  # гуль не затронут


async def test_ghoul_snap_does_not_affect_user_balance(
    user_service, ghoul_service, make_user
):
    await make_user(telegram_id=700_000_101)
    await ghoul_service.register(telegram_id=700_000_101)
    await user_service.plus_balance(telegram_id=700_000_101, change_balance=1000)

    await ghoul_service.snap_finger(telegram_id=700_000_101)

    user = await user_service.get(find_by=700_000_101)
    assert user.balance == 1000  # баланс не изменился


# --- Upgrade kagune требует баланса (через stat_upgrade) ---


async def test_kagune_strength_upgrades_independently(ghoul_service, make_user):
    await make_user(telegram_id=700_000_200)
    await ghoul_service.register(telegram_id=700_000_200)

    ghoul_before = await ghoul_service.get(find_by=700_000_200)
    strength_before = ghoul_before.kagune_strength

    await ghoul_service.upgrade_kagune(telegram_id=700_000_200)

    ghoul_after = await ghoul_service.get(find_by=700_000_200)
    assert ghoul_after.kagune_strength == strength_before + 1


# --- Консистентность данных после нескольких операций ---


async def test_full_player_lifecycle(user_service, ghoul_service, make_user):
    """Полный жизненный цикл: создание -> регистрация гуля -> действия -> проверка."""
    tid = 700_000_300
    await make_user(telegram_id=tid, username="lifecycle_user")

    # Регистрируем гуля
    reg = await ghoul_service.register(telegram_id=tid)
    assert reg.ok is True

    # Начисляем баланс
    await user_service.plus_balance(telegram_id=tid, change_balance=2000)

    # Снапаем несколько раз
    for _ in range(3):
        await ghoul_service.snap_finger(telegram_id=tid)

    # Пьём кофе
    await ghoul_service.coffee(telegram_id=tid)

    # Итоговая проверка
    user = await user_service.get(find_by=tid)
    ghoul = await ghoul_service.get(find_by=tid)

    assert user.balance == 2000
    assert user.race_bit == Race.GHOUL.value["bit"]
    assert ghoul.snap_count == 3
    assert ghoul.coffee_count == 1


async def test_user_lookup_by_username_after_register(
    user_service, ghoul_service, make_user
):
    """Пользователь доступен по username после всех операций."""
    await make_user(telegram_id=700_000_400, username="findme")
    await ghoul_service.register(telegram_id=700_000_400)
    await user_service.plus_balance(telegram_id=700_000_400, change_balance=100)

    user = await user_service.get(find_by="findme")
    assert user is not None
    assert user.balance == 100
    assert user.race_bit == Race.GHOUL.value["bit"]


async def test_minus_balance_after_ghoul_operations(
    user_service, ghoul_service, make_user
):
    """Списание баланса корректно работает после операций с гулем."""
    tid = 700_000_500
    await make_user(telegram_id=tid)
    await ghoul_service.register(telegram_id=tid)

    await user_service.plus_balance(telegram_id=tid, change_balance=1000)
    await ghoul_service.snap_finger(telegram_id=tid)
    await user_service.minus_balance(telegram_id=tid, change_balance=300)

    user = await user_service.get(find_by=tid)
    ghoul = await ghoul_service.get(find_by=tid)

    assert user.balance == 700
    assert ghoul.snap_count == 1


async def test_power_calculation_after_register(ghoul_service, make_user):
    """calculate_power возвращает корректное значение для только что созданного гуля."""
    await make_user(telegram_id=700_000_600)
    result = await ghoul_service.register(telegram_id=700_000_600)
    ghoul = result.ghoul

    power = ghoul_service.calculate_power(ghoul)

    # Дефолтные значения: strength=1, dexterity=1, speed=1,
    # max_health=5, regeneration=1, kagune_strength=1 -> сумма = 10
    assert power == 10


async def test_top_balance_ordering(user_service, make_user):
    """Топ баланса должен быть отсортирован по убыванию."""
    await make_user(telegram_id=700_000_700, username="poor")
    await make_user(telegram_id=700_000_701, username="rich")
    await make_user(telegram_id=700_000_702, username="medium")

    await user_service.plus_balance(telegram_id=700_000_700, change_balance=100)
    await user_service.plus_balance(telegram_id=700_000_701, change_balance=9999)
    await user_service.plus_balance(telegram_id=700_000_702, change_balance=500)

    top = await user_service.get_top_balance(limit=3)

    balances = [u.balance for u in top]
    assert balances == sorted(balances, reverse=True)
    assert top[0].balance == 9999
