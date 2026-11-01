"""Топы с параметром «чат»: «топ бал чат», «топ щелк чат», «топ бм чат», «топ кагуне чат»
считают только тех, кто сейчас в этом чате."""

import pytest
from sqlalchemy import insert

from src.bot.dialogs import Dialogs
from src.bot.types import KaguneType
from src.database.models import Family, FamilyMember

from .conftest import (
    button_data,
    matches_phrase,
    message_update,
    only_text,
    owner_dict,
    phrase_texts,
)
from .test_common_routers import seed
from .test_ghoul_routers import group_callback_update, seed_ghoul

GROUP = -100500
UID = 700001
NEIGHBOUR = 700002
OUTSIDER = 700003


@pytest.fixture
async def members(feed, telegram, session_factory):
    """Вася и Петя пишут в группе, Чужой есть в базе, но в группе не был."""
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    await seed(session_factory, OUTSIDER, "Чужой", balance=900)
    await seed_ghoul(session_factory, OUTSIDER, snap_count=90)
    for uid, name, snaps in ((UID, "Вася", 5), (NEIGHBOUR, "Петя", 10)):
        await seed(session_factory, uid, name, balance=snaps * 10)
        await seed_ghoul(session_factory, uid, snap_count=snaps)
        await feed(message_update("привет", uid=uid, first_name=name, chat=GROUP))


async def test_snap_top_of_the_chat_skips_players_outside_it(send, members):
    (reply,) = await send("топ щелк чат", uid=UID, chat=GROUP)

    snap_title = only_text(Dialogs.tops.snap_title(count=20))
    title = only_text(Dialogs.tops.in_chat(title=snap_title))
    rows = [
        only_text(Dialogs.tops.row(place=1, name="Петя", value=10)),
        only_text(Dialogs.tops.row(place=2, name="Вася", value=5)),
    ]
    you = only_text(Dialogs.tops.you(place=2, value=5))
    assert reply == only_text(Dialogs.tops.list(title=title, rows="\n".join(rows), you=you))


async def test_count_follows_the_chat_word(send, members):
    (reply,) = await send("top cp chat 1", uid=UID, chat=GROUP)

    power_title = only_text(Dialogs.tops.power_title(count=1))
    assert reply.startswith(only_text(Dialogs.tops.in_chat(title=power_title)))
    assert "Чужой" not in reply and len(reply.splitlines()) == 5
    assert matches_phrase(reply.splitlines()[-1], "tops.you")


async def test_family_counts_in_the_chat_if_one_of_its_members_is_there(
    send, members, session_factory
):
    async with session_factory() as session:
        family_id = await session.scalar(
            insert(Family).values(name=None, balance=500).returning(Family.id)
        )
        await session.execute(
            insert(FamilyMember),
            [
                dict(telegram_id=NEIGHBOUR, family_id=family_id),
                dict(telegram_id=OUTSIDER, family_id=family_id),
            ],
        )
        await session.commit()

    (reply,) = await send("топ бал чат", uid=UID, chat=GROUP)

    family = only_text(Dialogs.family.top_name(members="Петя, Чужой"))
    rows = [
        only_text(Dialogs.tops.balance.row(place=1, name=family, balance="500")),
        only_text(Dialogs.tops.balance.row(place=2, name="Вася", balance="50")),
    ]
    you = only_text(Dialogs.tops.you(place=2, value="50"))
    line = Dialogs.tops.balance.chat_message(count=20, rows="\n".join(rows), you=you)
    assert reply in phrase_texts(line)


async def test_kagune_buttons_keep_the_chat_scope(feed, members, session_factory):
    ukaku = KaguneType.UKAKU.value["bit"]
    await seed_ghoul(session_factory, UID, kagune_type_bit=ukaku, kagune_strength_ukaku=7)
    await seed_ghoul(session_factory, OUTSIDER, kagune_type_bit=ukaku, kagune_strength_ukaku=70)
    telegram = await feed(message_update("топ кагуне чат", uid=UID, chat=GROUP))
    (body,) = telegram.bodies("sendMessage")

    telegram = await feed(group_callback_update(button_data(body, "Укаку"), uid=UID))

    (edited,) = telegram.bodies("editMessageText")
    type_title = only_text(Dialogs.tops.kagune.type_title(count=20, kagune="Укаку"))
    assert edited["text"].startswith(only_text(Dialogs.tops.in_chat(title=type_title)))
    assert only_text(Dialogs.tops.row(place=1, name="Вася", value=7)) in edited["text"]
    assert "Чужой" not in edited["text"]


@pytest.mark.parametrize("text", ["топ бал чат", "топ щелк чат"])
async def test_chat_top_in_private_chat(send, session_factory, text):
    await seed(session_factory, UID, "Вася")
    await seed_ghoul(session_factory, UID)

    (reply,) = await send(text, uid=UID)

    assert reply == only_text(Dialogs.tops.chat_only_group())
