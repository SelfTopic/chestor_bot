"""Промокоды: создание админом (+промо, короткая и многострочная форма) и активация гулем
(промо <название>): награды, одна активация на игрока, лимит, срок."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from src.bot.dialogs import Dialogs
from src.bot.repositories import PromoRepository
from src.bot.routers.promo_rewards import STAT_LABELS
from src.bot.utils import utcnow_naive
from src.config import settings
from src.database.models import PromoActivation, PromoCode, UserCooldown

from .conftest import (
    button_data,
    callback_update,
    matches_phrase,
    message_update,
    only_text,
    phrase_texts,
    rich_texts,
)
from .test_common_routers import seed
from .test_ghoul_routers import balance_of, get_ghoul, seed_active_cooldown, seed_ghoul

ADMIN = 999
UID = 700001
OTHER = 700002


@pytest.fixture(autouse=True)
def admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADMIN_IDS", [ADMIN])


async def promo(session_factory, name: str) -> PromoCode | None:
    async with session_factory() as session:
        return await PromoRepository(session).live_by_name(name)


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
        (reply,) = await send("+промо лето 2 24ч\nчестоны 1000\n\nрс 200\nхп 5", uid=ADMIN)

        assert matches_phrase(reply, "admin.promo.created")
        code = await promo(session_factory, "лето")
        assert code is not None and code.expires_at is not None
        assert code.rewards == [
            {"kind": "cheston", "amount": 1000},
            {"kind": "rc", "amount": 200},
            {"kind": "stat", "stat": "max_health", "amount": 5},
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

    async def test_progress_over_full_level_levels_up_like_a_fight(self, send, session_factory):
        async with session_factory() as session:
            await PromoRepository(session).create(
                name="опыт",
                rewards=[{"kind": "progress", "percent": 50}],
                activations_limit=1,
                expires_at=None,
                created_by=ADMIN,
            )
            await session.commit()
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, level=1, level_progress=80)

        sent = await send("промо опыт", uid=UID)

        assert any(matches_phrase(text, "notify.level_up") for text in sent)
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        assert (ghoul.level, ghoul.level_progress) == (2, 0)

    async def test_stats_stop_at_the_level_cap(self, send, session_factory):
        async with session_factory() as session:
            await PromoRepository(session).create(
                name="сила",
                rewards=[
                    {"kind": "stat", "stat": "strength", "amount": 10},
                    {"kind": "stat", "stat": "max_health", "amount": 5},
                ],
                activations_limit=1,
                expires_at=None,
                created_by=ADMIN,
            )
            await session.commit()
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, level=1, strength=97, max_health=50, health=40)

        (reply,) = await send("промо сила", uid=UID)

        rewards = "\n".join(
            [
                only_text(Dialogs.promo.reward.stat_capped(stat=STAT_LABELS["strength"], amount=3)),
                only_text(Dialogs.promo.reward.stat(stat=STAT_LABELS["max_health"], amount=5)),
            ]
        )
        assert reply in phrase_texts(Dialogs.promo.activated(name="сила", rewards=rewards))
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        assert (ghoul.strength, ghoul.max_health, ghoul.health) == (100, 55, 45)

    async def test_full_hunger(self, send, session_factory):
        await send("+промо еда 1\nсытость", uid=ADMIN)
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, hunger=40)

        (reply,) = await send("промо еда", uid=UID)

        rewards = only_text(Dialogs.promo.reward.full_hunger())
        assert reply in phrase_texts(Dialogs.promo.activated(name="еда", rewards=rewards))
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        assert ghoul.hunger == 100

    async def test_heal_and_cooldown_reset(self, send, session_factory):
        await send("+промо отдых 1\nлечение\nсброс кд", uid=ADMIN)
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, health=10, max_health=50)
        await seed_active_cooldown(session_factory, UID, "SNAP")

        (reply,) = await send("промо отдых", uid=UID)

        rewards = "\n".join(
            [
                only_text(Dialogs.promo.reward.heal()),
                only_text(Dialogs.promo.reward.cooldown_reset()),
            ]
        )
        assert reply in phrase_texts(Dialogs.promo.activated(name="отдых", rewards=rewards))
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        assert ghoul.health == 50
        async with session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(UserCooldown)) == 0

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


async def card_body(feed, telegram, name: str) -> dict:
    await feed(message_update(f"/promo {name}", uid=ADMIN))
    (body,) = telegram.bodies("sendRichMessage")
    return body


async def press(feed, telegram, body: dict, label: str) -> dict:
    await feed(callback_update(button_data(body, label), uid=ADMIN))
    (edit,) = telegram.bodies("editMessageText")
    return edit


class TestManage:
    async def test_card_shows_rewards_activations_and_status(self, feed, telegram, session_factory):
        await add_promo(session_factory, "лето", amount=500, limit=10)

        texts = rich_texts(await card_body(feed, telegram, "ЛЕТО"))

        card = Dialogs.admin.promo.card
        assert only_text(Dialogs.admin.promo.status.active()) in texts
        assert cheston(500) in texts
        assert only_text(card.activations_value(used=0, limit=10)) in texts
        assert only_text(Dialogs.admin.promo.forever()) in texts

    async def test_unknown_name(self, send):
        (reply,) = await send("/promo зима", uid=ADMIN)
        assert reply == only_text(Dialogs.admin.promo.card.not_found(name="зима"))

    async def test_delete_after_confirmation_keeps_the_history(
        self, feed, send, telegram, session_factory
    ):
        await add_promo(session_factory, "лето")
        await add_ghoul(session_factory, UID)
        card = Dialogs.admin.promo.card

        confirm = await press(feed, telegram, await card_body(feed, telegram, "лето"), only_text(card.delete_button()))
        assert only_text(card.confirm_question()) in rich_texts(confirm)
        assert await promo(session_factory, "лето") is not None

        deleted = await press(feed, telegram, confirm, only_text(card.confirm_button()))
        assert only_text(Dialogs.admin.promo.status.deleted()) in rich_texts(deleted)
        assert await promo(session_factory, "лето") is None

        (reply,) = await send("промо лето", uid=UID)
        assert reply in phrase_texts(Dialogs.promo.not_found(name="лето"))

        texts = rich_texts(await card_body(feed, telegram, "лето"))
        assert only_text(Dialogs.admin.promo.status.deleted()) in texts
        assert only_text(card.deleted()) in texts

        await send("+промо лето 100 5", uid=ADMIN)
        assert await promo(session_factory, "лето") is not None

    async def test_catalog_pages_and_opens_a_card(self, feed, telegram, session_factory):
        for number in range(9):
            await add_promo(session_factory, f"код{number}")

        await feed(message_update("/promos", uid=ADMIN))
        (first,) = telegram.bodies("sendRichMessage")
        assert "код8" in rich_texts(first) and "код0" not in rich_texts(first)

        await feed(callback_update(button_data(first, "»"), uid=ADMIN))
        (second,) = telegram.bodies("editMessageText")
        assert "код0" in rich_texts(second)

        card = await press(feed, telegram, second, "код0")
        assert only_text(Dialogs.admin.promo.card.title(name="код0")) in rich_texts(card)

        back = await press(feed, telegram, card, only_text(Dialogs.admin.promo.card.back_button()))
        assert "код0" in rich_texts(back)
