"""Промокоды: создание админом (+промо, короткая и многострочная форма) и активация гулем
(промо <название>): награды, одна активация на игрока, лимит, срок."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from src.bot.dialogs import Dialogs
from src.bot.repositories import PromoRepository
from src.bot.utils import utcnow_naive
from src.config import settings
from src.database.models import PromoActivation, PromoCode

from .conftest import matches_phrase, only_text, phrase_texts
from .test_common_routers import seed
from .test_ghoul_routers import balance_of, get_ghoul, seed_ghoul

ADMIN = 999
UID = 700001
OTHER = 700002


@pytest.fixture(autouse=True)
def admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADMIN_IDS", [ADMIN])


async def promo(session_factory, name: str) -> PromoCode | None:
    async with session_factory() as session:
        return await PromoRepository(session).by_name(name)


async def add_promo(
    session_factory, name: str, amount: int = 500, limit: int = 10, expires_at: datetime | None = None
) -> None:
    async with session_factory() as session:
        await PromoRepository(session).create(
            name=name,
            rewards=[{"kind": "cheston", "amount": amount}],
            activations_limit=limit,
            expires_at=expires_at,
            created_by=ADMIN,
        )
        await session.commit()


async def add_ghoul(session_factory, telegram_id: int) -> None:
    await seed(session_factory, telegram_id, "Вася")
    await seed_ghoul(session_factory, telegram_id)


def cheston(amount: int) -> str:
    return only_text(Dialogs.promo.reward.cheston(amount=amount))


class TestCreate:
    async def test_short_form_gives_cheston_without_a_deadline(self, send, session_factory):
        (reply,) = await send("+промо Лето 500 30", uid=ADMIN)

        created = Dialogs.admin.promo.created(
            name="лето",
            activations=30,
            until=only_text(Dialogs.admin.promo.forever()),
            rewards=cheston(500),
        )
        assert reply == only_text(created)
        code = await promo(session_factory, "лето")
        assert code is not None
        assert (code.rewards, code.activations_limit, code.expires_at) == (
            [{"kind": "cheston", "amount": 500}],
            30,
            None,
        )

    async def test_reward_lines_and_a_deadline(self, send, session_factory):
        before = utcnow_naive()
        (reply,) = await send("+промо лето 2 24ч\nчестоны 1000\n\nрс 200", uid=ADMIN)

        assert matches_phrase(reply, "admin.promo.created")
        code = await promo(session_factory, "лето")
        assert code is not None and code.expires_at is not None
        assert code.rewards == [
            {"kind": "cheston", "amount": 1000},
            {"kind": "rc", "amount": 200},
        ]
        assert code.activations_limit == 2
        assert timedelta(hours=24) <= code.expires_at - before < timedelta(hours=24, minutes=1)

    async def test_unknown_reward_line_is_named(self, send, session_factory):
        (reply,) = await send("+промо лето 5\nкофе 3", uid=ADMIN)

        assert reply == only_text(Dialogs.admin.promo.bad_line(line="кофе 3"))
        assert await promo(session_factory, "лето") is None

    async def test_missing_numbers_show_usage(self, send):
        (reply,) = await send("+промо лето", uid=ADMIN)
        assert reply == only_text(Dialogs.admin.promo.usage())

    async def test_taken_name_is_refused(self, send, session_factory):
        await add_promo(session_factory, "лето")

        (reply,) = await send("+промо ЛЕТО 100 5", uid=ADMIN)
        assert reply == only_text(Dialogs.admin.promo.name_taken(name="ЛЕТО"))


class TestActivate:
    async def test_ghoul_gets_the_rewards_once(self, send, session_factory):
        await add_promo(session_factory, "лето", amount=500)
        await add_ghoul(session_factory, UID)
        balance = await balance_of(session_factory, UID)

        (reply,) = await send("промо ЛЕТО", uid=UID)
        activated = Dialogs.promo.activated(name="ЛЕТО", rewards=cheston(500))
        assert reply in phrase_texts(activated)
        assert await balance_of(session_factory, UID) == balance + 500

        (reply,) = await send("промо лето", uid=UID)
        assert reply in phrase_texts(Dialogs.promo.already(name="лето"))
        assert await balance_of(session_factory, UID) == balance + 500

    async def test_rc_count_towards_lifetime_earnings(self, send, session_factory):
        async with session_factory() as session:
            await PromoRepository(session).create(
                name="рс",
                rewards=[{"kind": "rc", "amount": 200}],
                activations_limit=1,
                expires_at=None,
                created_by=ADMIN,
            )
            await session.commit()
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, rc_money=10, lifetime_rc_earned=30)

        (reply,) = await send("промо рс", uid=UID)

        rewards = only_text(Dialogs.promo.reward.rc(amount=200))
        assert reply in phrase_texts(Dialogs.promo.activated(name="рс", rewards=rewards))
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        assert (ghoul.rc_money, ghoul.lifetime_rc_earned) == (210, 230)

    async def test_spent_code_leaves_no_activation(self, send, session_factory):
        await add_promo(session_factory, "лето", limit=1)
        await add_ghoul(session_factory, UID)
        await add_ghoul(session_factory, OTHER)
        await send("промо лето", uid=UID)
        balance = await balance_of(session_factory, OTHER)

        (reply,) = await send("промо лето", uid=OTHER)

        assert reply in phrase_texts(Dialogs.promo.exhausted(name="лето"))
        assert await balance_of(session_factory, OTHER) == balance
        async with session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(PromoActivation)) == 1

    async def test_expired_code(self, send, session_factory):
        await add_promo(session_factory, "лето", expires_at=utcnow_naive() - timedelta(minutes=1))
        await add_ghoul(session_factory, UID)

        (reply,) = await send("промо лето", uid=UID)
        assert reply in phrase_texts(Dialogs.promo.expired(name="лето"))

    async def test_unknown_code(self, send, session_factory):
        await add_ghoul(session_factory, UID)

        (reply,) = await send("промо зима", uid=UID)
        assert reply in phrase_texts(Dialogs.promo.not_found(name="зима"))
