"""Хештеги культа в нике: раз в час 10 000 CheSton и уведомление в личку с кнопкой «выключить»."""

from datetime import timedelta

from sqlalchemy import select, update

from src.bot.dialogs import Dialogs
from src.bot.game_configs import CULT_CONFIG
from src.bot.repositories import UserRepository
from src.bot.tasks import CultReward
from src.bot.utils import format_amount, utcnow_naive
from src.database.models import User

from .conftest import button_data, callback_update, only_text, phrase_texts

CULTIST = 700001
QUIET = 700002
STRANGER = 700003
REWARD = Dialogs.cult.reward(amount=format_amount(CULT_CONFIG.reward))


async def seed(session_factory, telegram_id: int, name: str, active_hours_ago: float) -> None:
    async with session_factory() as session:
        repo = UserRepository(session)
        await repo.upsert(
            telegram_id=telegram_id, first_name=name, has_private_chat=True, telegram_language="ru"
        )
        await repo.change_data(
            telegram_id, last_active_at=utcnow_naive() - timedelta(hours=active_hours_ago)
        )
        await session.commit()


async def balances(session_factory) -> dict[int, int]:
    async with session_factory() as session:
        rows = await session.execute(select(User.telegram_id, User.balance))
        return dict(rows.tuples().all())


async def an_hour_passes(session_factory) -> None:
    async with session_factory() as session:
        await session.execute(
            update(User).values(cult_rewarded_at=User.cult_rewarded_at - timedelta(hours=1))
        )
        await session.commit()


async def test_active_cultists_are_paid_once_an_hour(dispatcher, telegram, session_factory):
    await seed(session_factory, CULTIST, "Вася #РабЧестора", active_hours_ago=1)
    await seed(session_factory, QUIET, "Петя #честормойпапа", active_hours_ago=48)
    await seed(session_factory, STRANGER, "Коля #savetrueghouls", active_hours_ago=1)

    await dispatcher.run_task(CultReward)
    await dispatcher.run_task(CultReward)

    assert await balances(session_factory) == {CULTIST: CULT_CONFIG.reward, QUIET: 0, STRANGER: 0}
    (sent,) = telegram.bodies("sendMessage")
    assert sent["chat_id"] == CULTIST
    assert sent["text"] in phrase_texts(REWARD)

    await an_hour_passes(session_factory)
    await dispatcher.run_task(CultReward)
    assert (await balances(session_factory))[CULTIST] == 2 * CULT_CONFIG.reward


async def test_muted_cultist_keeps_getting_paid_silently(
    dispatcher, telegram, feed, session_factory
):
    await seed(session_factory, CULTIST, "Вася #рабчестора", active_hours_ago=1)
    await dispatcher.run_task(CultReward)
    (sent,) = telegram.bodies("sendMessage")

    press = callback_update(button_data(sent, only_text(Dialogs.cult.mute_button())), uid=CULTIST)
    # нажатие — тоже апдейт: бот обновит ник, и хештег в нём должен остаться
    press["callback_query"]["from"]["first_name"] = "Вася #рабчестора"
    await feed(press)
    (alert,) = telegram.bodies("answerCallbackQuery")
    assert alert["text"] in phrase_texts(Dialogs.cult.muted())

    telegram.calls.clear()
    await an_hour_passes(session_factory)
    await dispatcher.run_task(CultReward)
    assert telegram.bodies("sendMessage") == []
    assert (await balances(session_factory))[CULTIST] == 2 * CULT_CONFIG.reward
