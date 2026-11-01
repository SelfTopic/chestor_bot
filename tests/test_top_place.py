"""Строка «ты сейчас на N месте» внизу топов: место считается тем же порядком, что и список,
даже если сам игрок в показанные строки не попал."""

from src.bot.dialogs import Dialogs
from src.bot.types import KaguneType
from src.bot.utils import format_amount

from .conftest import button_data, callback_update, message_update, only_text
from .test_common_routers import seed
from .test_ghoul_routers import seed_ghoul
from .test_marriage import seed_family

UID = 700001
OTHERS = (700002, 700003)


async def test_place_is_shown_below_a_top_that_does_not_reach_it(send, session_factory):
    await seed(session_factory, UID, "Вася")
    await seed_ghoul(session_factory, UID, snap_count=1)
    for uid, snaps in zip(OTHERS, (5, 5), strict=True):
        await seed(session_factory, uid, f"Игрок{uid}")
        await seed_ghoul(session_factory, uid, snap_count=snaps)

    (reply,) = await send("топ щелк 1", uid=UID)

    assert reply.splitlines()[-1] == only_text(Dialogs.tops.you(place=3, value=1))


async def test_family_member_sees_the_place_of_the_family_wallet(send, session_factory):
    await seed(session_factory, UID, "Вася")
    await seed(session_factory, OTHERS[0], "Петя", balance=500)
    await seed(session_factory, OTHERS[1], "Коля")
    await seed_family(session_factory, UID, OTHERS[1], balance=300)

    (reply,) = await send("топ бал 1", uid=UID)

    you = Dialogs.tops.you(place=2, value=format_amount(300))
    assert reply.splitlines()[-1] == only_text(you)


async def test_kagune_type_the_player_lacks_is_not_his_top(feed, session_factory):
    await seed(session_factory, UID, "Вася")
    await seed_ghoul(
        session_factory,
        UID,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=7,
    )
    telegram = await feed(message_update("топ кагуне", uid=UID))
    (body,) = telegram.bodies("sendMessage")
    assert body["text"].splitlines()[-1] == only_text(Dialogs.tops.you(place=1, value=7))

    telegram = await feed(callback_update(button_data(body, "Бикаку"), uid=UID))

    (edited,) = telegram.bodies("editMessageText")
    assert edited["text"].splitlines()[-1] == only_text(Dialogs.tops.you_absent())

