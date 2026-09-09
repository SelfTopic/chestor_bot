"""Health/max_health прокачивается по другой цене/потолку, чем остальные
4 стата - см. живую симуляцию боевого движка (scripts/battle_log_all_kagune.py),
которая показала, что честный многораундовый бой получается только при
health ~2.5x от боевых статов, а не 1:1."""

from src.bot.game_configs import STAT_UPGRADE_CONFIG, stat_cap_for_level
from src.bot.repositories.balances_log import BalancesLogRepository
from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.dialog import DialogService
from src.bot.services.ghoul import GhoulService
from src.bot.services.stat_upgrade import StatUpgradeService
from src.bot.services.user import UserService


# --- Чистая логика конфигов (game_configs.py) -------------------------------


def test_max_health_cap_is_2_5x_other_stats():
    assert stat_cap_for_level(1, "max_health") == 250
    assert stat_cap_for_level(1, "strength") == 100
    assert stat_cap_for_level(1, "") == 100  # дефолт для "прочих" статов


def test_max_health_price_per_point_is_discounted():
    default_price = STAT_UPGRADE_CONFIG.price(100, 10)
    health_price = STAT_UPGRADE_CONFIG.price(100, 10, "max_health")
    assert health_price == int(default_price * 0.4)


# --- Сквозная проверка через сам сервис -------------------------------------


def _make_stat_service(session) -> StatUpgradeService:
    ghoul_service = GhoulService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
    )
    user_service = UserService(
        user_repository=UserRepository(session),
        ghoul_repository=GhoulRepository(session),
        user_cooldown_repository=UserCooldownRepository(session),
        chat_repository=ChatRepository(session),
        balances_log_repository=BalancesLogRepository(session),
    )
    return StatUpgradeService(
        ghoul_service=ghoul_service,
        user_service=user_service,
        dialog_service=DialogService(),
    )


async def test_build_message_shows_higher_cap_for_max_health(
    make_user, make_ghoul, session
):
    telegram_id = 700_100_001
    await make_user(telegram_id=telegram_id)
    await make_ghoul(telegram_id=telegram_id, level=1, max_health=100, strength=100)

    service = _make_stat_service(session)
    ghoul = await service.ghoul_service.get(telegram_id)
    user = await service.user_service.get(find_by=telegram_id)

    assert service._cap(ghoul, "max_health") == 250
    assert service._cap(ghoul, "strength") == 100

    text, _ = service.build_message(ghoul, user)
    assert "❤️Макс. здоровье: 100" in text
    assert "💪Сила: 100  х5: —" in text  # уже упёрлись в потолок 100


async def test_purchase_charges_discounted_price_for_max_health(
    make_user, make_ghoul, session
):
    telegram_id = 700_100_002
    await make_user(telegram_id=telegram_id)
    await make_ghoul(telegram_id=telegram_id, level=5, max_health=1, strength=1)

    service = _make_stat_service(session)
    await service.user_service.plus_balance(
        telegram_id=telegram_id, change_balance=10_000_000, log="test"
    )

    _, _, bought_health, price_health = await service.purchase(
        telegram_id=telegram_id, stat_key="max_health", count=10
    )
    _, _, bought_strength, price_strength = await service.purchase(
        telegram_id=telegram_id, stat_key="strength", count=10
    )

    assert bought_health == 10
    assert bought_strength == 10
    assert price_health == int(price_strength * 0.4)
