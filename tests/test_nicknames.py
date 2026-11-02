"""Ник игрока в группе: «ник <текст>», «-ник», снятие модератором реплаем. В своём чате бот
зовёт игрока ником, в другом чате и в личке — именем из Telegram, в модерации — ником с
настоящим именем."""

import pytest

from src.bot.dialogs import Dialogs
from src.bot.repositories import ModerationRepository
from src.bot.repositories.user_names import UserNameRepository
from src.bot.types import ModerationActionType
from src.bot.utils import format_amount

from .conftest import chat_member_update, only_text, owner_dict, phrase_texts

GROUP = -100900
OTHER = -100901
UID = 41
ADMIN = 501
nick = Dialogs.nickname


@pytest.fixture(autouse=True)
def admins(telegram):
    telegram.results["getChatAdministrators"] = [owner_dict(ADMIN)]


async def say(send, text: str, chat: int | None = GROUP, uid: int = UID, **kwargs) -> list[str]:
    names = {UID: "Аня", ADMIN: "Админ"}
    return await send(text, uid=uid, first_name=names.get(uid, "Петя"), chat=chat, **kwargs)


async def test_nickname_is_used_only_in_its_own_chat(send):
    (reply,) = await say(send, "ник Королева")
    assert reply in phrase_texts(nick.set(nickname="Королева"))
    assert await say(send, "ник") == [only_text(nick.current(nickname="Королева"))]

    for chat, name in ((GROUP, "Королева"), (OTHER, "Аня"), (None, "Аня")):
        (reply,) = await say(send, "бал", chat=chat)
        assert reply in phrase_texts(Dialogs.balance(balance=format_amount(0), name=name))


@pytest.mark.parametrize(
    ("text", "chat", "phrase"),
    [
        ("ник " + "я" * 33, GROUP, nick.too_long(limit=32)),
        ("ник @durov", GROUP, nick.link()),
        ("ник заходи на t.me/spam", GROUP, nick.link()),
        ("ник Королева", None, nick.only_group()),
    ],
)
async def test_bad_nicknames_are_refused(send, text, chat, phrase):
    assert await say(send, text, chat=chat) == [only_text(phrase)]
    assert await say(send, "ник") == [only_text(nick.none(limit=32))]


async def test_nickname_outlives_leaving_the_chat_until_removed(send, feed):
    await say(send, "ник Королева")
    await feed(chat_member_update(UID, GROUP, "member", "left", first_name="Аня"))

    assert await say(send, "ник") == [only_text(nick.current(nickname="Королева"))]
    (reply,) = await say(send, "-ник")
    assert reply in phrase_texts(nick.cleared(name="Аня"))
    assert await say(send, "-ник") == [only_text(nick.nothing_to_clear())]


async def test_only_a_moderator_removes_someone_elses_nickname(send):
    await say(send, "ник Королева")

    assert await say(send, "-ник", uid=42, reply_to_uid=UID, reply_to_name="Аня") == []
    replies = await say(send, "-ник", uid=ADMIN, reply_to_uid=UID, reply_to_name="Аня")

    removed = nick.cleared_by_moderator(moderator="Админ", name="Аня", nickname="Королева")
    assert replies == [only_text(removed)]
    assert await say(send, "ник") == [only_text(nick.none(limit=32))]


async def test_moderation_shows_the_real_name_next_to_the_nickname(send, session_factory):
    await say(send, "ник Королева")
    await say(send, "привет", uid=ADMIN)
    async with session_factory() as session:
        await ModerationRepository(session).insert_action(
            GROUP, ADMIN, UID, ModerationActionType.MUTE, None, None
        )
        await session.commit()

    (reply,) = await say(send, "мутлист", uid=ADMIN)

    shown = only_text(nick.with_real(nickname="Королева", name="Аня"))
    item = Dialogs.moderation.lists.item(
        place=1, name=shown, moderator="Админ", term=Dialogs.moderation.term.forever()
    )
    assert reply.splitlines()[-1] == only_text(item)


async def test_names_for_a_chat_prefer_its_nicknames(send, session_factory):
    await say(send, "ник Королева")
    await say(send, "привет", chat=OTHER)

    async with session_factory() as session:
        names = UserNameRepository(session)
        assert await names.names([UID], GROUP) == {UID: "Королева"}
        assert await names.names([UID], OTHER) == {UID: "Аня"}
