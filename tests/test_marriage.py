"""Браки — это семьи любого размера, где все в браке со всеми. Предложение платное: сначала
платит зовущий, потом, когда согласились все (новенький в группе, члены семьи в личке бота),
платит новенький, и все его деньги уходят на общий счёт семьи. Развод бесплатный: ушедший
остаётся ни с чем, а последний оставшийся забирает счёт распавшейся семьи."""

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select, update

from src.bot.dialogs import Dialogs
from src.bot.game_configs import MARRIAGE_CONFIG
from src.bot.repositories import FamilyRepository
from src.bot.routers.common.marriage.render import mention
from src.database.models import Family, MarriageProposal

from .conftest import button_data, callback_update, message_update, only_text, owner_dict, phrase_texts
from .test_common_routers import seed
from .test_ghoul_routers import balance_of, seed_ghoul

A, B, C, D = 700001, 700002, 700003, 700004
NAMES = {A: "Вася", B: "Петя", C: "Коля", D: "Дима"}
GROUP = -100500
PRICE = MARRIAGE_CONFIG.proposal_price
RICH = 600_000


@pytest.fixture(autouse=True)
def group_admins(telegram):
    telegram.results["getChatAdministrators"] = [owner_dict(99)]


async def seed_players(session_factory, **balances: int) -> None:
    for uid, name in NAMES.items():
        await seed(session_factory, uid, name, balance=balances.get(name, 0))


async def seed_family(session_factory, *members: int, balance: int = 0) -> None:
    async with session_factory() as session:
        families = FamilyRepository(session)
        family = await families.create_family()
        for uid in members:
            await families.add_member(family.id, uid)
        await families.change_balance(family.id, balance)
        await session.commit()


def who(uid: int) -> str:
    return mention(uid, NAMES[uid])


def press(data: str, uid: int, message_id: int = 44) -> dict[str, Any]:
    update = callback_update(data, uid=uid)
    update["callback_query"]["from"]["first_name"] = NAMES[uid]
    update["callback_query"]["message"]["message_id"] = message_id
    return update


async def family_of(session_factory, uid: int) -> tuple[list[int], int] | None:
    async with session_factory() as session:
        families = FamilyRepository(session)
        family_id = await families.family_id_of(uid)
        if family_id is None:
            return None
        family = await families.family(family_id)
        assert family is not None
        members = await families.members(family_id)
        return [m.telegram_id for m in members], family.balance


async def proposal_stage(session_factory) -> str:
    async with session_factory() as session:
        (proposal,) = await session.scalars(select(MarriageProposal))
        return proposal.stage


@pytest.fixture
def propose(feed, telegram):
    """Зовущий отвечает «брак» на сообщение новенького и платит; отдаёт сообщение-приглашение."""

    async def _propose(proposer: int, target: int) -> dict[str, Any]:
        await feed(
            message_update(
                "брак", uid=proposer, first_name=NAMES[proposer], chat=GROUP,
                reply_to_uid=target, reply_to_name=NAMES[target],
            )
        )
        (ask,) = telegram.bodies("sendMessage")
        pay = only_text(Dialogs.marriage.buttons.pay(price=PRICE))
        await feed(press(button_data(ask, pay), proposer))
        (invite,) = telegram.bodies("editMessageText")
        return invite

    return _propose


def consent_button(invite: dict[str, Any], label) -> str:
    return button_data(invite, only_text(label))


async def test_two_singles_marry_and_pool_their_money(feed, telegram, session_factory, propose):
    await seed_players(session_factory, Вася=RICH, Петя=300_000)

    invite = await propose(A, B)

    assert await balance_of(session_factory, A) == RICH - PRICE
    proposer_button = consent_button(invite, Dialogs.marriage.buttons.proposer())
    target_button = consent_button(invite, Dialogs.marriage.buttons.target())
    await feed(press(proposer_button, A))
    assert await family_of(session_factory, A) is None

    await feed(press(target_button, B))

    (married,) = telegram.bodies("editMessageText")
    members = f"{who(A)}, {who(B)}"
    assert married["text"] in phrase_texts(Dialogs.marriage.married(target=who(B), members=members))
    pooled = RICH - PRICE + 300_000 - MARRIAGE_CONFIG.acceptance_price
    assert await family_of(session_factory, A) == ([A, B], pooled)
    assert (await balance_of(session_factory, A), await balance_of(session_factory, B)) == (0, 0)


async def test_newcomer_joins_only_when_every_member_agrees_in_private(
    feed, send, telegram, session_factory, propose
):
    await seed_players(session_factory, Коля=RICH)
    await seed_family(session_factory, A, B, balance=RICH)

    invite = await propose(A, C)
    await feed(press(consent_button(invite, Dialogs.marriage.buttons.proposer()), A))
    await feed(press(consent_button(invite, Dialogs.marriage.buttons.target()), C))
    assert await family_of(session_factory, C) is None

    (stranger,) = await send("/start marry_1", uid=D, first_name=NAMES[D])
    assert stranger == only_text(Dialogs.marriage.link_not_family())

    await send("/start marry_1", uid=B, first_name=NAMES[B])
    (vote,) = telegram.bodies("sendMessage")
    assert vote["text"] in phrase_texts(Dialogs.marriage.family_vote(proposer=who(A), target=who(C)))
    await feed(press(button_data(vote, only_text(Dialogs.marriage.buttons.family_vote())), B, 55))

    pooled = RICH - PRICE + RICH - MARRIAGE_CONFIG.acceptance_price
    assert await family_of(session_factory, A) == ([A, B, C], pooled)
    edited = {body["message_id"]: body["text"] for body in telegram.bodies("editMessageText")}
    assert edited[55] == only_text(Dialogs.marriage.family_voted())


@pytest.mark.parametrize("by_family", [False, True])
async def test_one_refusal_cancels_the_proposal_and_burns_the_money(
    feed, send, telegram, session_factory, propose, by_family
):
    await seed_players(session_factory, Коля=RICH)
    await seed_family(session_factory, A, B, balance=RICH)
    invite = await propose(A, C)

    if by_family:
        await send("/start marry_1", uid=B, first_name=NAMES[B])
        (vote,) = telegram.bodies("sendMessage")
        no = only_text(Dialogs.marriage.buttons.family_decline())
        await feed(press(button_data(vote, no), B, 55))
    else:
        await feed(press(consent_button(invite, Dialogs.marriage.buttons.decline()), C))

    assert await proposal_stage(session_factory) == "declined"
    refused_by = B if by_family else C
    declined = Dialogs.marriage.declined(name=who(refused_by), proposer=who(A), price=PRICE)
    invite_edit = next(b for b in telegram.bodies("editMessageText") if b["message_id"] == 44)
    assert invite_edit["text"] in phrase_texts(declined)
    assert await family_of(session_factory, A) == ([A, B], RICH - PRICE)


@pytest.mark.parametrize(
    ("balances", "target", "refusal"),
    [
        ({"Вася": RICH}, A, Dialogs.marriage.refusals.self()),
        ({"Вася": PRICE - 1}, B, Dialogs.marriage.refusals.not_enough_money(price=PRICE)),
    ],
)
async def test_proposal_refusals(send, session_factory, balances, target, refusal):
    await seed_players(session_factory, **balances)

    (reply,) = await send("брак", uid=A, chat=GROUP, reply_to_uid=target)

    assert reply in phrase_texts(refusal)


async def test_someone_already_married_cannot_be_called(feed, send, session_factory, propose):
    await seed_players(session_factory, Вася=RICH, Петя=RICH, Коля=RICH)
    invite = await propose(A, B)
    await feed(press(consent_button(invite, Dialogs.marriage.buttons.proposer()), A))
    await feed(press(consent_button(invite, Dialogs.marriage.buttons.target()), B))

    (reply,) = await send(f"свадьба {B}", uid=C, chat=GROUP)

    assert reply in phrase_texts(Dialogs.marriage.refusals.target_married())


async def test_clickable_name_is_a_target_and_plain_chatter_is_not(send, telegram, session_factory):
    await seed_players(session_factory, Вася=RICH)
    entity = {"type": "text_mention", "offset": 5, "length": 4, "user": {"id": B, "is_bot": False, "first_name": "Петя"}}

    assert await send("брак — это скучно", uid=A, chat=GROUP) == []
    await send("брак Петя", uid=A, chat=GROUP, entities=[entity])

    (ask,) = telegram.bodies("sendMessage")
    assert ask["text"] == only_text(Dialogs.marriage.ask(proposer=who(A), target=who(B), price=PRICE))


async def test_broke_newcomer_cannot_agree(feed, telegram, session_factory, propose):
    await seed_players(session_factory, Вася=RICH, Петя=1)
    invite = await propose(A, B)

    await feed(press(consent_button(invite, Dialogs.marriage.buttons.target()), B))

    (alert,) = telegram.bodies("answerCallbackQuery")
    price = MARRIAGE_CONFIG.acceptance_price
    assert alert["text"] == only_text(Dialogs.marriage.consent.not_enough_money(price=price))
    assert await proposal_stage(session_factory) == "awaiting"


async def test_an_hour_without_everyone_burns_the_proposal(
    dispatcher, telegram, session_factory, propose
):
    await seed_players(session_factory, Вася=RICH, Петя=RICH)
    await propose(A, B)
    async with session_factory() as session:
        await session.execute(
            update(MarriageProposal).values(
                created_at=MarriageProposal.created_at - timedelta(hours=2)
            )
        )
        await session.commit()
    telegram.calls.clear()

    await dispatcher.marriage_ticker.tick()

    assert await proposal_stage(session_factory) == "expired"
    (edit,) = telegram.bodies("editMessageText")
    assert edit["text"] in phrase_texts(Dialogs.marriage.expired(proposer=who(A), price=PRICE))
    assert await balance_of(session_factory, A) == RICH - PRICE


async def test_divorce_leaves_with_nothing_and_the_last_one_keeps_the_account(
    feed, telegram, session_factory
):
    await seed_players(session_factory)
    await seed_family(session_factory, A, B, C, balance=900_000)

    async def divorce(uid: int) -> None:
        await feed(message_update("развод", uid=uid, first_name=NAMES[uid], chat=GROUP))
        (ask,) = telegram.bodies("sendMessage")
        await feed(press(button_data(ask, only_text(Dialogs.divorce.button())), uid))

    await divorce(A)
    assert await family_of(session_factory, B) == ([B, C], 900_000)
    assert await balance_of(session_factory, A) == 0

    await divorce(B)
    (edit,) = telegram.bodies("editMessageText")
    dissolved = Dialogs.divorce.dissolved(name=who(B), heir=who(C), amount=900_000)
    assert edit["text"] == only_text(dissolved)
    assert await family_of(session_factory, C) is None
    assert await balance_of(session_factory, C) == 900_000
    async with session_factory() as session:
        (family,) = await session.scalars(select(Family))
        assert (family.balance, family.dissolved_at is not None) == (0, True)


async def test_family_shares_one_account_and_one_line_in_the_top(send, session_factory):
    await seed_players(session_factory, Коля=700)
    await seed_family(session_factory, A, B, balance=1000)

    (balance,) = await send("бал", uid=B, first_name=NAMES[B])
    (top,) = await send("топ бал 2", uid=C, first_name=NAMES[C])

    assert balance in phrase_texts(Dialogs.balance(balance="1000", name=NAMES[B]))
    family = only_text(Dialogs.family.top_name(members="Вася, Петя"))
    rows = "\n".join(
        only_text(Dialogs.tops.balance.row(place=place, name=name, balance=amount))
        for place, (name, amount) in enumerate([(family, 1000), ("Коля", 700)], start=1)
    )
    assert top == only_text(Dialogs.tops.balance.message(count=2, rows=rows))


async def test_spouses_neither_duel_nor_transfer_to_each_other(send, session_factory):
    await seed_players(session_factory)
    await seed_family(session_factory, A, B, balance=1000)
    await seed_ghoul(session_factory, A)

    (duel,) = await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B)
    (transfer,) = await send("/transfer 10", uid=A, reply_to_uid=B)

    assert duel in phrase_texts(Dialogs.duel.refusals.spouses())
    assert transfer in phrase_texts(Dialogs.transfer.errors.spouse())
