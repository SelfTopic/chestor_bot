import pytest
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select

from src.bot.game_configs import LEVEL_UP_CONFIG
from src.bot.repositories.balances_log import BalancesLogRepository
from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.repositories.user import UserRepository
from src.bot.repositories.user_coldown import UserCooldownRepository
from src.bot.services.dialog import DialogService
from src.bot.services.ghoul import GhoulService
from src.bot.services.level_up import LevelUpService
from src.bot.services.user import UserService
from src.database.models import User


class FakeBot:
    """По умолчанию просто копит отправленные сообщения. can_send=False
    имитирует самый частый в этом проекте случай - юзер играл только в
    чате, ни разу не открыв бота в личке, Telegram отказывает в отправке."""

    def __init__(self, can_send: bool = True):
        self.can_send = can_send
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str):
        if not self.can_send:
            raise TelegramForbiddenError(
                method=None, message="Forbidden: bot can't initiate conversation"
            )
        self.sent.append((chat_id, text))


def _make_level_up_service(session, bot):
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
    return LevelUpService(
        user_service=user_service,
        ghoul_service=ghoul_service,
        dialog_service=DialogService(),
        bot=bot,
    )


async def test_level_up_increments_level(make_user, make_ghoul, session):
    await make_user(telegram_id=700_000_001)
    await make_ghoul(telegram_id=700_000_001, level=1)

    service = _make_level_up_service(session, FakeBot())
    result = await service.level_up(700_000_001)

    assert result.ghoul.level == 2


async def test_level_up_grants_cheston_reward_in_range(make_user, make_ghoul, session):
    await make_user(telegram_id=700_000_002)
    await make_ghoul(telegram_id=700_000_002, level=1)

    service = _make_level_up_service(session, FakeBot())
    result = await service.level_up(700_000_002)  # -> уровень 2

    assert 2000 <= result.cheston_reward <= 20000

    user = await session.scalar(select(User).where(User.telegram_id == 700_000_002))
    assert user.balance == result.cheston_reward


async def test_level_up_grants_rc_reward_in_range(make_user, make_ghoul, session):
    await make_user(telegram_id=700_000_003)
    await make_ghoul(telegram_id=700_000_003, level=1, rc_money=0)
    rc_before = 0  # захвачено отдельно от ORM-объекта - тот же session identity
    # map мутирует ghoul.rc_money на месте после increment_fields

    service = _make_level_up_service(session, FakeBot())
    result = await service.level_up(700_000_003)  # -> уровень 2

    assert 10 <= result.rc_reward <= 40
    assert result.ghoul.rc_money == rc_before + result.rc_reward
    assert result.ghoul.lifetime_rc_earned == result.rc_reward


async def test_level_up_reward_ranges_scale_with_new_level(
    make_user, make_ghoul, session
):
    await make_user(telegram_id=700_000_004)
    await make_ghoul(telegram_id=700_000_004, level=4)  # -> станет 5м

    service = _make_level_up_service(session, FakeBot())
    result = await service.level_up(700_000_004)

    assert result.ghoul.level == 5
    assert 5000 <= result.cheston_reward <= 50000
    assert 25 <= result.rc_reward <= 100


async def test_level_up_shows_stat_cap_shift_in_notification(
    make_user, make_ghoul, session
):
    await make_user(telegram_id=700_000_005)
    await make_ghoul(telegram_id=700_000_005, level=1)

    bot = FakeBot()
    service = _make_level_up_service(session, bot)
    await service.level_up(700_000_005)

    assert len(bot.sent) == 1
    _, text = bot.sent[0]
    assert "Регенерация: 100 -> 200" in text
    assert "Сила: 100 -> 200" in text


async def test_level_up_applies_reward_even_if_dm_fails(
    make_user, make_ghoul, session
):
    """Ключевое требование: игрок, который ни разу не открывал бота в
    личке, всё равно обязан получить уровень и награду."""
    await make_user(telegram_id=700_000_006)
    await make_ghoul(telegram_id=700_000_006, level=1)

    bot = FakeBot(can_send=False)
    service = _make_level_up_service(session, bot)
    result = await service.level_up(700_000_006)

    assert result.notified is False
    assert result.ghoul.level == 2

    user = await session.scalar(select(User).where(User.telegram_id == 700_000_006))
    assert user.balance == result.cheston_reward
    assert result.ghoul.rc_money == result.rc_reward


async def test_level_up_notified_true_on_success(make_user, make_ghoul, session):
    await make_user(telegram_id=700_000_007)
    await make_ghoul(telegram_id=700_000_007, level=1)

    service = _make_level_up_service(session, FakeBot(can_send=True))
    result = await service.level_up(700_000_007)

    assert result.notified is True


async def test_level_up_raises_for_unknown_ghoul(session):
    service = _make_level_up_service(session, FakeBot())
    with pytest.raises(ValueError, match="Ghoul not found"):
        await service.level_up(999_999_999)


async def test_ghoul_repository_increment_fields_is_atomic_across_columns(
    make_user, make_ghoul, session
):
    await make_user(telegram_id=700_000_008)
    await make_ghoul(telegram_id=700_000_008, level=1, rc_money=10)

    repo = GhoulRepository(session)
    updated = await repo.increment_fields(700_000_008, level=1, rc_money=5)

    assert updated.level == 2
    assert updated.rc_money == 15


async def test_ghoul_repository_increment_fields_requires_at_least_one_field(session):
    repo = GhoulRepository(session)
    with pytest.raises(ValueError):
        await repo.increment_fields(700_000_009)


async def test_add_progress_accumulates_without_levelup(make_user, make_ghoul, session):
    await make_user(telegram_id=700_000_010)
    await make_ghoul(telegram_id=700_000_010, level=1, level_progress=10.0)

    service = _make_level_up_service(session, FakeBot())
    result = await service.add_progress(700_000_010, 20.0)

    assert result.progress == 30.0
    assert result.levels_gained == 0
    assert result.level_up_results == []
    assert result.ghoul.level == 1


async def test_add_progress_triggers_levelup_on_overflow_and_discards_excess(
    make_user, make_ghoul, session
):
    """Уровень не должен перепрыгивать значения - излишек выше 100%
    (здесь 15%) отбрасывается, а не переносится на новый уровень."""
    await make_user(telegram_id=700_000_011)
    await make_ghoul(telegram_id=700_000_011, level=1, level_progress=90.0)

    service = _make_level_up_service(session, FakeBot())
    result = await service.add_progress(700_000_011, 25.0)  # 90+25=115 -> +1 уровень

    assert result.levels_gained == 1
    assert result.progress == 0.0
    assert result.ghoul.level == 2
    assert len(result.level_up_results) == 1
    assert result.level_up_results[0].ghoul.level == 2


async def test_add_progress_huge_delta_still_gives_only_one_levelup(
    make_user, make_ghoul, session
):
    """Даже огромная дельта за один вызов не должна давать больше одного
    уровня - см. правку "уровень никогда не перепрыгивает значения"."""
    await make_user(telegram_id=700_000_012)
    await make_ghoul(telegram_id=700_000_012, level=1, level_progress=0.0)

    service = _make_level_up_service(session, FakeBot())
    result = await service.add_progress(700_000_012, 100.0)  # максимум по /add_progress

    assert result.levels_gained == 1
    assert result.progress == 0.0
    assert result.ghoul.level == 2
    assert len(result.level_up_results) == 1


async def test_add_progress_can_levelup_repeatedly_across_separate_calls(
    make_user, make_ghoul, session
):
    await make_user(telegram_id=700_000_015)
    await make_ghoul(telegram_id=700_000_015, level=1, level_progress=0.0)

    service = _make_level_up_service(session, FakeBot())

    result = await service.add_progress(700_000_015, 100.0)
    assert result.levels_gained == 1
    assert result.ghoul.level == 2

    # отдельный, второй вызов - снова ровно один уровень, не два сразу
    result2 = await service.add_progress(700_000_015, 100.0)
    assert result2.levels_gained == 1
    assert result2.ghoul.level == 3


async def test_add_progress_negative_delta_reduces_progress_without_levelup(
    make_user, make_ghoul, session
):
    await make_user(telegram_id=700_000_013)
    await make_ghoul(telegram_id=700_000_013, level=3, level_progress=50.0)

    service = _make_level_up_service(session, FakeBot())
    result = await service.add_progress(700_000_013, -30.0)

    assert result.progress == 20.0
    assert result.levels_gained == 0
    assert result.ghoul.level == 3


async def test_add_progress_grants_reward_for_each_levelup_even_if_dm_fails(
    make_user, make_ghoul, session
):
    await make_user(telegram_id=700_000_014)
    await make_ghoul(telegram_id=700_000_014, level=1, level_progress=90.0)

    bot = FakeBot(can_send=False)
    service = _make_level_up_service(session, bot)
    result = await service.add_progress(700_000_014, 10.0)  # ровно 100 -> левел-ап

    assert result.levels_gained == 1
    assert result.ghoul.level == 2
    assert result.level_up_results[0].notified is False

    user = await session.scalar(select(User).where(User.telegram_id == 700_000_014))
    assert user.balance == result.level_up_results[0].cheston_reward


async def test_add_progress_raises_for_unknown_ghoul(session):
    service = _make_level_up_service(session, FakeBot())
    with pytest.raises(ValueError, match="Ghoul not found"):
        await service.add_progress(999_999_998, 10.0)
