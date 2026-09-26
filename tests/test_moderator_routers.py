"""routers/moderator_routers: настройка чата (правила/приветствие/прощание). В отличие
от CreatorMiddleware (settings.ADMIN_IDS), ModeratorMiddleware проверяет живым
getChatMember — только админ/создатель супергруппы, молчит и для private/group/channel,
и для не-админа в супергруппе."""

from src.bot.exceptions.chat import ChatRulesError

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

        # исправленный прод-баг: у прода в тексте оставался пробел в начале
        assert reply == "Правила чата обновлены: \n\nНе спамить"

    async def test_multiline_rules_keep_line_breaks(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        (reply,) = await send(
            "Новые правила\n1. Не спамить\n2. Не флудить  ", uid=ADMIN, chat=GROUP
        )

        assert reply == "Правила чата обновлены: \n\n1. Не спамить\n2. Не флудить"

    async def test_empty_rules_are_rejected(self, send, telegram):
        # как у прода: пустые правила отвергает ChatService, ответ — global_error
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        (reply,) = await send("новые правила", uid=ADMIN, chat=GROUP)

        assert reply.startswith("Ошибка: Кол-во символов в правилах")
        (error,) = send.dispatcher.errors
        assert isinstance(error, ChatRulesError)
        send.dispatcher.errors.clear()  # ошибка ожидаемая

    async def test_glued_word_is_not_a_command(self, send, telegram):
        # исправленный прод-баг: "новые правилаX" ловилось по началу текста
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        assert await send("новые правилаX", uid=ADMIN, chat=GROUP) == []


class TestSetWelcome:
    async def test_sets_welcome_and_strips_prefix(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        (reply,) = await send("новое приветствие Здравствуй!", uid=ADMIN, chat=GROUP)

        assert reply == "Приветственное сообщение обновлено: \n\nЗдравствуй!"


class TestSetGoodbye:
    async def test_sets_goodbye_and_strips_prefix(self, send, telegram):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        telegram.results["getChatMember"] = owner_dict(ADMIN)

        (reply,) = await send("новое прощание Пока!", uid=ADMIN, chat=GROUP)

        assert reply == "Прощальное сообщение обновлено: \n\nПока!"
