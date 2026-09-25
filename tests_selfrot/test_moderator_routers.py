"""routers/moderator_routers: настройка чата (правила/приветствие/прощание). В отличие
от CreatorMiddleware (settings.ADMIN_IDS), ModeratorMiddleware проверяет живым
getChatMember — только админ/создатель супергруппы, молчит и для private/group/channel,
и для не-админа в супергруппе."""

from .conftest import admin_dict, member_dict, owner_dict

ADMIN = 501
GROUP = -100777


class TestModeratorMiddleware:
    async def test_private_chat_is_ignored(self, send, telegram):
        telegram.results["getChatMember"] = owner_dict(42)

        assert await send("новые правила текст", uid=42) == []

    async def test_non_admin_in_group_is_ignored(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = member_dict("member", ADMIN)

        assert await send("новые правила текст", uid=ADMIN, chat=GROUP) == []

    async def test_admin_gets_through(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = admin_dict(ADMIN)

        assert await send("новые правила текст", uid=ADMIN, chat=GROUP) != []

    async def test_creator_gets_through(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        assert await send("новые правила текст", uid=ADMIN, chat=GROUP) != []


class TestSetRules:
    async def test_sets_rules_and_strips_prefix(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        (reply,) = await send("новые правила Не спамить", uid=ADMIN, chat=GROUP)

        # префикс без пробела на конце: как у прода, пробел перед текстом остаётся
        assert reply == "Правила чата обновлены: \n\n Не спамить"


class TestSetWelcome:
    async def test_sets_welcome_and_strips_prefix(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        (reply,) = await send("новое приветствие Здравствуй!", uid=ADMIN, chat=GROUP)

        assert reply == "Приветственное сообщение обновлено: \n\n Здравствуй!"


class TestSetGoodbye:
    async def test_sets_goodbye_and_strips_prefix(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        (reply,) = await send("новое прощание Пока!", uid=ADMIN, chat=GROUP)

        assert reply == "Прощальное сообщение обновлено: \n\n Пока!"
