"""«мутлист», «банлист», «варнлист», «киклист»: действующие наказания чата с пагинацией,
только для модераторов. Кончившиеся по сроку, снятые и перекрытые не показываются, кик —
пока кикнутый не вернулся в чат."""

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import update

from src.bot.dialogs import Dialogs
from src.bot.repositories import ModerationRepository
from src.bot.types import ModerationActionType
from src.database.models import ModerationAction, ModerationWarning

from .conftest import (
    admin_dict,
    button_data,
    callback_update,
    chat_dict,
    chat_member_update,
    matches_phrase,
    message_update,
    only_text,
    owner_dict,
)
from .test_common_routers import seed

GROUP = -100777
ADMIN = 501
lists = Dialogs.moderation.lists
FOREVER = only_text(Dialogs.moderation.term.forever())
MUTE = ModerationActionType.MUTE
BAN = ModerationActionType.BAN
KICK = ModerationActionType.KICK


@pytest.fixture(autouse=True)
async def staff(telegram, session_factory):
    telegram.results["getChatAdministrators"] = [owner_dict(ADMIN)]
    await seed(session_factory, ADMIN, "Админ")
    for uid, name in ((41, "Аня"), (42, "Петя"), (43, "Коля")):
        await seed(session_factory, uid, name)


async def record(
    session_factory,
    target: int,
    action: ModerationActionType,
    seconds: int | None = None,
    reason: str | None = None,
    ago: timedelta = timedelta(),
) -> None:
    async with session_factory() as session:
        repository = ModerationRepository(session)
        row = await repository.insert_action(GROUP, ADMIN, target, action, seconds, reason)
        if ago:
            await session.execute(
                update(ModerationAction)
                .where(ModerationAction.id == row.id)
                .values(
                    created_at=ModerationAction.created_at - ago,
                    expires_at=ModerationAction.expires_at - ago,
                )
            )
        await session.commit()


def item(place: int, name: str, reason: str | None = None) -> str:
    who = dict(place=place, name=name, moderator="Админ", term=FOREVER)
    if reason is None:
        return only_text(lists.item(**who))
    return only_text(lists.item_for(reason=reason, **who))


def page(title, *items: str) -> str:
    return only_text(lists.page(title=only_text(title), items="\n".join(items)))


def says(text: str, uid: int = ADMIN) -> dict[str, Any]:
    return message_update(text, uid=uid, first_name="Админ", chat=GROUP)


async def show(feed, text: str) -> dict[str, Any]:
    telegram = await feed(says(text))
    (body,) = telegram.bodies("sendMessage")
    return body


async def test_mutelist_shows_active_mutes_newest_first(feed, session_factory):
    await record(session_factory, 41, MUTE, reason="флуд")
    await record(session_factory, 42, MUTE, seconds=3600)
    await record(session_factory, 43, MUTE, seconds=600, ago=timedelta(hours=1))
    await record(session_factory, 41, MUTE)

    body = await show(feed, "мутлист")

    title, _, *lines = body["text"].splitlines()
    assert title == only_text(lists.mute_title(count=2))
    assert lines[0] == item(1, "Аня")
    assert matches_phrase(lines[1], "moderation.lists.item") and lines[1].startswith("2. Петя")


async def test_unmute_and_kick_end_mutes_and_bans(feed, session_factory):
    await record(session_factory, 41, MUTE)
    await record(session_factory, 41, ModerationActionType.UNMUTE)
    await record(session_factory, 42, BAN)
    await record(session_factory, 42, KICK)
    await record(session_factory, 43, BAN, reason="спам")

    assert (await feed(says("мутлист"))).sent == [
        only_text(lists.mute_empty())
    ]
    body = await show(feed, "/banlist")
    assert body["text"] == page(lists.ban_title(count=1), item(1, "Коля", "спам"))


async def test_warnlist_skips_revoked_and_burnt_warns(feed, session_factory):
    async with session_factory() as session:
        repository = ModerationRepository(session)
        for target, reason in ((41, "мат"), (42, None), (43, None)):
            await repository.add_warning(GROUP, ADMIN, target, reason, None)
        await session.execute(
            update(ModerationWarning)
            .where(ModerationWarning.target_id == 42)
            .values(revoked_at=ModerationWarning.created_at)
        )
        await session.execute(
            update(ModerationWarning)
            .where(ModerationWarning.target_id == 43)
            .values(expires_at=ModerationWarning.created_at - timedelta(minutes=1))
        )
        await session.commit()

    body = await show(feed, "варнлист")

    assert body["text"] == page(lists.warn_title(count=1), item(1, "Аня", "мат"))


async def test_kick_leaves_the_kicklist_when_the_member_comes_back(feed, session_factory):
    await feed(says("привет"))
    await record(session_factory, 41, KICK, ago=timedelta(hours=2))
    await record(session_factory, 42, KICK, reason="реклама", ago=timedelta(hours=1))
    await feed(chat_member_update(41, GROUP, "left", "member", first_name="Аня"))

    body = await show(feed, "киклист")

    ago = only_text(Dialogs.moderation.term.hours(count=1))
    kick = lists.kick_item_for(place=1, name="Петя", ago=ago, moderator="Админ", reason="реклама")
    assert body["text"] == page(lists.kick_title(count=1), only_text(kick))


async def test_pages_turn_only_for_moderators(feed, telegram, session_factory):
    for _ in range(12):
        await record(session_factory, 41, BAN)
        await record(session_factory, 41, ModerationActionType.UNBAN)
    for _ in range(12):
        await record(session_factory, 42, MUTE)
        await record(session_factory, 43, MUTE)
    for uid in range(100, 112):
        await seed(session_factory, uid, f"Игрок{uid}")
        await record(session_factory, uid, MUTE)

    body = await show(feed, "мутлист")
    assert len(body["text"].splitlines()) == 2 + 10

    forward = callback_update(button_data(body, "»"), uid=ADMIN)
    forward["callback_query"]["message"]["chat"] = chat_dict(GROUP)
    edited = (await feed(forward)).bodies("editMessageText")
    places = [line.split(".")[0] for line in edited[0]["text"].splitlines()[2:]]
    assert places == ["11", "12", "13", "14"]

    stranger = callback_update(button_data(body, "»"), uid=77)
    stranger["callback_query"]["message"]["chat"] = chat_dict(GROUP)
    telegram = await feed(stranger)
    (answer,) = telegram.bodies("answerCallbackQuery")
    assert answer["text"] == only_text(lists.only_moderators())
    assert telegram.methods_called("editMessageText") == 0


async def test_admin_without_ban_right_is_refused(feed, telegram, session_factory):
    telegram.results["getChatAdministrators"] = [owner_dict(99), admin_dict(ADMIN)]

    (reply,) = (await feed(says("банлист"))).sent

    assert matches_phrase(reply, "moderation.neutral.moderator_lacks_right")


async def test_members_get_no_answer(feed):
    assert (await feed(says("киклист", uid=42))).sent == []
