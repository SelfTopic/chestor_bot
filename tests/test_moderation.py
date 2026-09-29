"""routers/moderator_routers/punishments: мут, бан, кик и их снятие. Модератор — админ Telegram с нужным
правом; права, бот и цель берутся из getChatAdministrators / getChatMember."""

import time
from typing import Any

import pytest
from sqlalchemy import select, update

from selfrot.types import ChatMemberRestricted, ChatPermissions
from src.bot.dialogs import Dialogs
from src.bot.repositories import ChatRepository, ModerationRepository
from src.bot.types import ModerationActionType, ModerationVoice
from src.bot.types.insert import ChatInsert
from src.database.models import ModerationAction, ModerationSettings

from .conftest import (
    admin_dict,
    chat_dict,
    member_dict,
    only_text,
    owner_dict,
    phrase_texts,
    user_dict,
)
from .test_common_routers import seed

GROUP = -100777
ADMIN = 501
TARGET = 42
BOT = 1
ANONYMOUS_BOT = 1087968824

term = Dialogs.moderation.term
neutral = Dialogs.moderation.neutral
RESTRICT_RIGHT = only_text(Dialogs.moderation.right.restrict_members())


def bot_admin(can_restrict_members: bool = True) -> dict[str, Any]:
    return {
        **admin_dict(BOT),
        "user": {**user_dict(BOT, "B"), "is_bot": True},
        "can_restrict_members": can_restrict_members,
    }


def restricted_dict(
    uid: int, first_name: str, can_send_messages: bool
) -> dict[str, Any]:
    flags = {
        name: False
        for name, field in ChatMemberRestricted.model_fields.items()
        if field.is_required() and name not in ("status", "user")
    }
    return {
        **flags,
        "status": "restricted",
        "user": user_dict(uid, first_name),
        "is_member": True,
        "can_send_messages": can_send_messages,
        "until_date": 0,
    }


@pytest.fixture(autouse=True)
def chat_staff(telegram):
    telegram.results["getChatAdministrators"] = [owner_dict(ADMIN), bot_admin()]
    telegram.results["getChatMember"] = member_dict("member", TARGET, "Петя")
    telegram.results["restrictChatMember"] = True
    telegram.results["banChatMember"] = True
    telegram.results["unbanChatMember"] = True


async def journal(session_factory) -> list[ModerationAction]:
    async with session_factory() as session:
        rows = await session.scalars(
            select(ModerationAction).order_by(ModerationAction.id)
        )
        return list(rows)


async def set_settings(session_factory, **values: Any) -> None:
    async with session_factory() as session:
        await ChatRepository(session).upsert(
            ChatInsert(
                telegram_id=GROUP, title="группа", username=None, creator_id=ADMIN
            )
        )
        await ModerationRepository(session).settings(GROUP)
        await session.execute(update(ModerationSettings).values(**values))
        await session.commit()


def minutes(count: int):
    return term.limited(duration=term.minutes(count=count))


class TestMute:
    async def test_mute_by_reply_with_term_and_reason(
        self, send, telegram, session_factory
    ):
        (reply,) = await send(
            "мут 1 час 30 мин флуд и мат", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET
        )

        duration = (
            f"{only_text(term.hours(count=1))} {only_text(term.minutes(count=30))}"
        )
        assert reply in phrase_texts(
            neutral.muted_for(
                name="Петя",
                term=term.limited(duration=duration),
                reason="флуд и мат",
            )
        )
        (body,) = telegram.bodies("restrictChatMember")
        assert (body["chat_id"], body["user_id"]) == (GROUP, TARGET)
        assert not any(
            ChatPermissions.model_validate(body["permissions"]).model_dump().values()
        )
        assert abs(body["until_date"] - (time.time() + 5400)) < 10
        (row,) = await journal(session_factory)
        assert (row.chat_id, row.moderator_id, row.target_id, row.action) == (
            GROUP,
            ADMIN,
            TARGET,
            ModerationActionType.MUTE,
        )
        assert (row.duration_seconds, row.reason) == (5400, "флуд и мат")

    async def test_explicit_target_without_term_gets_chat_default(
        self, send, telegram, session_factory
    ):
        await seed(session_factory, TARGET, "Петя", username="petya")
        await set_settings(session_factory, mute_default_seconds=3600)

        (reply,) = await send("/mute @petya", uid=ADMIN, chat=GROUP)

        assert reply in phrase_texts(
            neutral.muted(name="Петя", term=term.limited(duration=term.hours(count=1)))
        )
        (body,) = telegram.bodies("restrictChatMember")
        assert body["user_id"] == TARGET
        (row,) = await journal(session_factory)
        assert (row.duration_seconds, row.reason) == (3600, None)

    async def test_forever(self, send, telegram, session_factory):
        (reply,) = await send(
            "мут навсегда", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET
        )

        assert reply in phrase_texts(neutral.muted(name="Петя", term=term.forever()))
        (body,) = telegram.bodies("restrictChatMember")
        assert "until_date" not in body
        (row,) = await journal(session_factory)
        assert row.duration_seconds is None

    async def test_term_outside_telegram_limits_is_refused(
        self, send, telegram, session_factory
    ):
        (reply,) = await send("мут 10с", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(
            neutral.term_out_of_range(
                min=term.seconds(count=30), max=term.days(count=366)
            )
        )
        assert telegram.bodies("restrictChatMember") == []
        assert await journal(session_factory) == []

    async def test_member_is_ignored_silently(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99), bot_admin()]

        assert await send("мут", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET) == []
        assert telegram.bodies("restrictChatMember") == []

    async def test_admin_without_right_is_told_which(self, send, telegram):
        telegram.results["getChatAdministrators"] = [
            owner_dict(99),
            admin_dict(ADMIN),
            bot_admin(),
        ]

        (reply,) = await send("мут", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(
            neutral.moderator_lacks_right(right=RESTRICT_RIGHT)
        )
        assert telegram.bodies("restrictChatMember") == []

    async def test_anonymous_admin_is_refused(self, send, telegram):
        (reply,) = await send(
            "мут",
            uid=ANONYMOUS_BOT,
            chat=GROUP,
            reply_to_uid=TARGET,
            sender_chat=chat_dict(GROUP),
        )

        assert reply in phrase_texts(neutral.anonymous())
        assert telegram.bodies("restrictChatMember") == []

    @pytest.mark.parametrize(
        "bot",
        [[bot_admin(can_restrict_members=False)], []],
        ids=["no right", "not admin"],
    )
    async def test_bot_without_right_says_which(self, send, telegram, bot):
        telegram.results["getChatAdministrators"] = [owner_dict(ADMIN), *bot]

        (reply,) = await send("мут", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(neutral.bot_lacks_right(right=RESTRICT_RIGHT))
        assert telegram.bodies("restrictChatMember") == []

    async def test_admin_cannot_be_muted(self, send, telegram):
        telegram.results["getChatMember"] = admin_dict(TARGET)

        (reply,) = await send("мут", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(neutral.target_is_admin(name="Админ"))
        assert telegram.bodies("restrictChatMember") == []

    async def test_usage_without_target(self, send):
        (reply,) = await send("мут", uid=ADMIN, chat=GROUP)

        assert reply in phrase_texts(neutral.mute_usage())

    async def test_unknown_username(self, send):
        (reply,) = await send("мут @nobody 5м", uid=ADMIN, chat=GROUP)

        assert reply in phrase_texts(neutral.user_not_found(query="@nobody"))

    async def test_rough_voice(self, send, session_factory):
        await set_settings(session_factory, voice=ModerationVoice.ROUGH)

        (reply,) = await send("мут 30м", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(
            Dialogs.moderation.rough.muted(name="Петя", term=minutes(30))
        )


class TestUnmute:
    async def test_unmute_lifts_restrictions(self, send, telegram, session_factory):
        telegram.results["getChatMember"] = restricted_dict(TARGET, "Петя", False)

        (reply,) = await send("размут", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(neutral.unmuted(name="Петя"))
        (body,) = telegram.bodies("restrictChatMember")
        assert body["user_id"] == TARGET
        assert all(
            ChatPermissions.model_validate(body["permissions"]).model_dump().values()
        )
        (row,) = await journal(session_factory)
        assert (row.action, row.duration_seconds) == (ModerationActionType.UNMUTE, None)

    async def test_not_muted(self, send, telegram, session_factory):
        (reply,) = await send("/unmute", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(neutral.not_muted(name="Петя"))
        assert telegram.bodies("restrictChatMember") == []
        assert await journal(session_factory) == []


class TestBan:
    async def test_ban_uses_ban_default_and_keeps_reason(
        self, send, telegram, session_factory
    ):
        await seed(session_factory, TARGET, "Петя", username="petya")
        await set_settings(session_factory, ban_default_seconds=7200)

        (reply,) = await send("/ban @petya реклама", uid=ADMIN, chat=GROUP)

        assert reply in phrase_texts(
            neutral.banned_for(
                name="Петя",
                term=term.limited(duration=term.hours(count=2)),
                reason="реклама",
            )
        )
        (body,) = telegram.bodies("banChatMember")
        assert (body["chat_id"], body["user_id"]) == (GROUP, TARGET)
        assert abs(body["until_date"] - (time.time() + 7200)) < 10
        assert "revoke_messages" not in body
        (row,) = await journal(session_factory)
        assert (row.action, row.duration_seconds, row.reason) == (
            ModerationActionType.BAN,
            7200,
            "реклама",
        )

    async def test_unban_lifts_ban_without_returning(
        self, send, telegram, session_factory
    ):
        telegram.results["getChatMember"] = member_dict("kicked", TARGET, "Петя")

        (reply,) = await send("разбан", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(neutral.unbanned(name="Петя"))
        (body,) = telegram.bodies("unbanChatMember")
        assert (body["user_id"], body["only_if_banned"]) == (TARGET, True)
        (row,) = await journal(session_factory)
        assert row.action == ModerationActionType.UNBAN

    async def test_unban_not_banned(self, send, telegram, session_factory):
        (reply,) = await send("/unban", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(neutral.not_banned(name="Петя"))
        assert telegram.bodies("unbanChatMember") == []
        assert await journal(session_factory) == []


class TestKick:
    async def test_kick_bans_then_unbans_and_all_text_is_reason(
        self, send, telegram, session_factory
    ):
        (reply,) = await send(
            "кик 30м флуд", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET
        )

        assert reply in phrase_texts(neutral.kicked_for(name="Петя", reason="30м флуд"))
        methods = [method for method, _ in telegram.calls]
        assert methods.index("banChatMember") < methods.index("unbanChatMember")
        (ban,) = telegram.bodies("banChatMember")
        assert "until_date" not in ban
        (unban,) = telegram.bodies("unbanChatMember")
        assert unban["only_if_banned"] is True
        (row,) = await journal(session_factory)
        assert (row.action, row.duration_seconds, row.reason) == (
            ModerationActionType.KICK,
            None,
            "30м флуд",
        )

    @pytest.mark.parametrize("status", ["left", "kicked"])
    async def test_absent_member_is_not_kicked(
        self, send, telegram, session_factory, status
    ):
        telegram.results["getChatMember"] = member_dict(status, TARGET, "Петя")

        (reply,) = await send("кик", uid=ADMIN, chat=GROUP, reply_to_uid=TARGET)

        assert reply in phrase_texts(neutral.target_absent(name="Петя"))
        assert telegram.bodies("banChatMember") == []
        assert telegram.bodies("unbanChatMember") == []
        assert await journal(session_factory) == []
