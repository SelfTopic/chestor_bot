"""routers/creator_routers: админ-команды за CreatorMiddleware. Админ — settings.ADMIN_IDS
(здесь uid=999, патчится autouse-фикстурой), проверка молчания для остальных — отдельно."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.bot.repositories import ChatRepository, GhoulRepository, UserRepository
from src.bot.types import KaguneType
from src.config import settings
from src.database.models import Cooldown
from src.bot.routers.creator_routers.media import USAGE as ADD_GIF_USAGE
from src.bot.services.broadcast import BroadcastService
from src.bot.services.notify import NotifyError, SelfrotBotNotifier

from .conftest import message_update, owner_dict
from .test_common_routers import seed
from .test_update_middlewares import get_user

ADMIN = 999


@pytest.fixture(autouse=True)
def admin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "ADMIN_IDS", [ADMIN])


async def get_ghoul(session_factory, telegram_id: int):
    async with session_factory() as session:
        return await GhoulRepository(session).get(telegram_id)


class TestCreatorMiddleware:
    async def test_non_admin_is_ignored_silently(self, send):
        assert await send("/ban_bot @nobody", uid=7) == []

    async def test_admin_gets_through(self, send, session_factory):
        await seed(session_factory, 42, "Цель")

        assert await send("/ban_bot @nobody", uid=ADMIN) != []


class TestBan:
    async def test_ban_by_reply_with_duration_and_reason(
        self, feed, telegram, session_factory
    ):
        await seed(session_factory, 42, "Вася")

        # у прода это давало перманентный бан с причиной "читерство читерство",
        # а "7d" терялось (см. docstring ban.py)
        await feed(message_update("/ban_bot 7d читерство", uid=ADMIN, reply_to_uid=42))

        user = await get_user(session_factory, 42)
        assert user is not None and user.is_banned
        assert user.ban_reason == "читерство"
        assert user.banned_until is not None
        assert user.banned_until > datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(days=6)

    async def test_ban_by_explicit_target_permanent(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        (reply,) = await send("/ban_bot @vasya", uid=ADMIN)
        assert "заблокирован навсегда" in reply

        user = await get_user(session_factory, 42)
        assert user is not None and user.is_banned

    async def test_already_banned(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася", is_banned=True)

        telegram.calls.clear()
        await feed(message_update("/ban_bot причина", uid=ADMIN, reply_to_uid=42))

        assert telegram.sent == ["⚠️ Пользователь уже забанен."]

    async def test_target_not_found(self, send):
        (reply,) = await send("/ban_bot @nobody", uid=ADMIN)
        assert "не найден" in reply

    async def test_unban_by_reply(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася", is_banned=True)

        await feed(message_update("/unban", uid=ADMIN, reply_to_uid=42))

        user = await get_user(session_factory, 42)
        assert user is not None and not user.is_banned

    async def test_unban_explicit_not_banned(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        assert await send("/unban @vasya", uid=ADMIN) == ["⚠️ Пользователь не забанен."]


class TestPlayersLookup:
    async def test_profile_found(self, send, session_factory):
        await seed(session_factory, 42, "Вася", balance=500)

        (reply,) = await send("/admin_profile 42", uid=ADMIN)
        assert "Вася" in reply and "500" in reply

    async def test_profile_not_found(self, send):
        assert await send("/admin_profile @nobody", uid=ADMIN) == [
            "❌ Пользователь не найден."
        ]

    async def test_usage_on_missing_argument(self, send):
        (reply,) = await send("/admin_profile", uid=ADMIN)
        assert reply.startswith("Использование:")


class TestStatsEdit:
    async def test_set_stat_by_reply_two_words(self, feed, telegram, session_factory):
        # у прода `/set_stat поле значение` реплаем падал с IndexError (см. docstring)
        await seed(session_factory, 42, "Вася", balance=100)

        await feed(message_update("/set_stat balance 250", uid=ADMIN, reply_to_uid=42))

        user = await get_user(session_factory, 42)
        assert user is not None and user.balance == 250

    async def test_set_stat_explicit(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya", balance=100)

        (reply,) = await send("/set_stat @vasya balance 300", uid=ADMIN)
        assert "установлено в <code>300</code>" in reply

    async def test_ghoul_field(self, send, session_factory):
        await seed(session_factory, 42, "Вася")
        async with session_factory() as session:
            await GhoulRepository(session).upsert(telegram_id=42)
            await session.commit()

        (reply,) = await send("/set_stat 42 level 5", uid=ADMIN)
        assert "гуля" in reply

        ghoul = await get_ghoul(session_factory, 42)
        assert ghoul is not None and ghoul.level == 5

    async def test_unknown_field(self, send, session_factory):
        await seed(session_factory, 42, "Вася")

        (reply,) = await send("/set_stat 42 nonsense 1", uid=ADMIN)
        assert "Неизвестное поле" in reply

    async def test_usage_lists_fields(self, send):
        (reply,) = await send("/set_stat", uid=ADMIN)
        assert reply.startswith("Использование: /set_stat")
        assert "Поля пользователя" in reply


class TestReset:
    async def test_reset_ghoul_by_reply(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася")
        async with session_factory() as session:
            await GhoulRepository(session).upsert(telegram_id=42)
            await session.commit()

        await feed(message_update("/reset_ghoul", uid=ADMIN, reply_to_uid=42))

        assert await get_ghoul(session_factory, 42) is None
        assert await get_user(session_factory, 42) is not None  # только гуль удалён

    async def test_reset_ghoul_not_found(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        assert await send("/reset_ghoul @vasya", uid=ADMIN) == [
            "⚠️ Профиль гуля не найден."
        ]

    async def test_reset_user_explicit(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        (reply,) = await send("/reset_user @vasya", uid=ADMIN)
        assert "полностью удалён" in reply
        assert await get_user(session_factory, 42) is None


class TestKill:
    async def test_kill_by_reply_with_cause(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася")
        async with session_factory() as session:
            await GhoulRepository(session).upsert(telegram_id=42)
            await session.commit()

        await feed(message_update("/kill_ghoul дуэль", uid=ADMIN, reply_to_uid=42))

        ghoul = await get_ghoul(session_factory, 42)
        assert ghoul is not None and ghoul.is_dead

    async def test_kill_explicit_default_cause(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")
        async with session_factory() as session:
            await GhoulRepository(session).upsert(telegram_id=42)
            await session.commit()

        (reply,) = await send("/kill_ghoul @vasya", uid=ADMIN)
        assert "причина: admin" in reply

    async def test_kill_no_ghoul(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        (reply,) = await send("/kill_ghoul @vasya", uid=ADMIN)
        assert reply.startswith("❌")

    async def test_kill_target_not_found(self, send):
        (reply,) = await send("/kill_ghoul @nobody", uid=ADMIN)
        assert "не найден" in reply


class TestCooldownAdmin:
    async def seed_cooldown(
        self, session_factory, telegram_id: int, name: str = "SNAP"
    ):
        async with session_factory() as session:
            from src.bot.repositories.user_coldown import UserCooldownRepository

            session.add(Cooldown(name=name, duration=60))
            await session.flush()
            await UserCooldownRepository(session).set_cooldown(telegram_id, name)
            await session.commit()

    async def test_clear_specific_by_reply(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася")
        await self.seed_cooldown(session_factory, 42)

        await feed(message_update("/clear_cooldown snap", uid=ADMIN, reply_to_uid=42))

        assert telegram.sent == ["✅ Кулдаун SNAP сброшен."]

    async def test_clear_all_explicit(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")
        await self.seed_cooldown(session_factory, 42)

        assert await send("/clear_cooldown @vasya all", uid=ADMIN) == [
            "✅ Сброшено кулдаунов: 1."
        ]

    async def test_unknown_type(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        (reply,) = await send("/clear_cooldown @vasya nonsense", uid=ADMIN)
        assert reply.startswith("❌ Неизвестный тип")

    async def test_nothing_to_clear(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")
        # тип зарегистрирован (иначе была бы "неизвестный тип"), но активного нет
        async with session_factory() as session:
            session.add(Cooldown(name="OTHER", duration=60))
            await session.commit()

        (reply,) = await send("/clear_cooldown @vasya other", uid=ADMIN)
        assert "не было активного кулдауна" in reply


class TestKaguneAdmin:
    # GhoulService.get() (grant/revoke идут через него) считает telegram_id > 666000
    # настоящим telegram_id, а меньшие — своим внутренним id гуля; тот же приём, что в
    # test_common_routers.py для расового профиля.
    UID = 700010

    async def seed_ghoul(self, session_factory, telegram_id: int):
        await seed(session_factory, telegram_id, "Вася", username="vasya")
        async with session_factory() as session:
            await GhoulRepository(session).upsert(telegram_id=telegram_id)
            await session.commit()

    async def test_give_all_by_reply(self, feed, telegram, session_factory):
        await self.seed_ghoul(session_factory, self.UID)

        await feed(message_update("/give_kagune all", uid=ADMIN, reply_to_uid=self.UID))

        ghoul = await get_ghoul(session_factory, self.UID)
        assert ghoul is not None
        for kt in KaguneType:
            assert getattr(ghoul, kt.value["strength_column"]) is not None

    async def test_give_specific_explicit(self, send, session_factory):
        await self.seed_ghoul(session_factory, self.UID)
        name = next(iter(KaguneType)).value["name_english"]

        (reply,) = await send(f"/give_kagune @vasya {name}", uid=ADMIN)
        assert reply.startswith("✅ Выдан тип")

    async def test_give_unknown_type(self, send, session_factory):
        await self.seed_ghoul(session_factory, self.UID)

        (reply,) = await send("/give_kagune @vasya nonsense", uid=ADMIN)
        assert reply.startswith("❌ Неизвестный тип")

    async def test_remove(self, send, session_factory):
        await self.seed_ghoul(session_factory, self.UID)
        first = next(iter(KaguneType))

        # нельзя убрать последний оставшийся тип, поэтому сначала выдаём все
        await send("/give_kagune @vasya all", uid=ADMIN)
        (reply,) = await send(
            f"/remove_kagune @vasya {first.value['name_english']}", uid=ADMIN
        )

        assert reply.startswith("✅ Тип")


class TestMedia:
    """/add_gif: сохраняет медиа из ответа в src/assets/<тип>/<коллекция>/ и в БД."""

    FILE_ID = "TEST_ADD_GIF_FILE"

    @pytest.fixture(autouse=True)
    def cleanup(self):
        created: list[Path] = []
        self.created = created
        yield
        for path in created:
            Path(path).unlink(missing_ok=True)

    def animation_reply(self, file_id: str = FILE_ID) -> dict:
        return {
            "animation": {
                "file_id": file_id,
                "file_unique_id": "u",
                "width": 1,
                "height": 1,
                "duration": 1,
            }
        }

    def video_reply(self, file_id: str = FILE_ID) -> dict:
        return {
            "video": {
                "file_id": file_id,
                "file_unique_id": "u",
                "width": 1,
                "height": 1,
                "duration": 1,
            }
        }

    def mock_download(self, telegram, file_id: str, content: bytes = b"gif-bytes"):
        telegram.results["getFile"] = {
            "file_id": file_id,
            "file_unique_id": "u",
            "file_path": f"documents/{file_id}",
        }
        telegram.set_file(f"documents/{file_id}", content)

    async def get_media_row(self, session_factory, path: str):
        from sqlalchemy import select

        from src.database.models import Media

        async with session_factory() as session:
            return await session.scalar(select(Media).where(Media.path == path))

    async def test_saves_animation_and_replies(self, feed, telegram, session_factory):
        self.mock_download(telegram, self.FILE_ID)
        path = (
            Path("src/assets/animation/snap_finger") / f"animation_{self.FILE_ID}.mp4"
        )
        self.created.append(path)

        await feed(
            message_update(
                "/add_gif snap",
                uid=ADMIN,
                reply_to_uid=42,
                reply_extra=self.animation_reply(),
            )
        )

        assert path.exists() and path.read_bytes() == b"gif-bytes"
        (sent,) = telegram.bodies("sendAnimation")
        assert "успешно скачано" in sent["caption"]

        row = await self.get_media_row(session_factory, str(path))
        assert row is not None
        assert row.telegram_file_id == self.FILE_ID
        assert row.collection == "snap_finger:animation"
        assert row.uploaded_by == ADMIN

    async def test_saves_video(self, feed, telegram):
        self.mock_download(telegram, self.FILE_ID)
        path = Path("src/assets/video/death") / f"video_{self.FILE_ID}.mp4"
        self.created.append(path)

        await feed(
            message_update(
                "/add_gif death",
                uid=ADMIN,
                reply_to_uid=42,
                reply_extra=self.video_reply(),
            )
        )

        assert path.exists()
        assert telegram.bodies("sendVideo")

    def test_kagune_collection_gets_a_subfolder(self):
        # ветка на диск не пишет (часть src/assets в этом окружении принадлежит root,
        # см. docstring target_path), поэтому только сама сборка пути
        from src.bot.services.media import CollectionParser
        from src.bot.types import MediaDownloadType
        from src.bot.routers.creator_routers.media import target_path

        collection = CollectionParser.parse("kagune ukaku")

        path = target_path(MediaDownloadType.ANIMATION, collection, self.FILE_ID)

        assert path == Path(
            f"src/assets/animation/upgrade_kagune/ukaku/animation_{self.FILE_ID}.mp4"
        )

    def test_non_kagune_collection_has_no_subfolder(self):
        from src.bot.services.media import CollectionParser
        from src.bot.types import MediaDownloadType
        from src.bot.routers.creator_routers.media import target_path

        collection = CollectionParser.parse("snap")

        path = target_path(MediaDownloadType.ANIMATION, collection, self.FILE_ID)

        assert path == Path(
            f"src/assets/animation/snap_finger/animation_{self.FILE_ID}.mp4"
        )

    async def test_unknown_collection(self, feed, telegram):
        telegram_response = await feed(
            message_update(
                "/add_gif nonsense",
                uid=ADMIN,
                reply_to_uid=42,
                reply_extra=self.animation_reply(),
            )
        )

        assert "не найдена" in telegram_response.sent[0]
        assert telegram.downloads == []  # до скачивания не дошло

    async def test_no_media_in_reply(self, send):
        assert await send("/add_gif snap", uid=ADMIN, reply_to_uid=42) == [
            "В выбранном вами сообщении отсутствует гиф или видео"
        ]

    async def test_missing_collection_argument(self, send):
        assert await send(
            "/add_gif", uid=ADMIN, reply_to_uid=42, reply_extra=self.animation_reply()
        ) == [ADD_GIF_USAGE]

    async def test_no_reply_is_ignored(self, send):
        assert await send("/add_gif snap", uid=ADMIN) == []

    async def test_duplicate_path_is_rejected(self, feed, telegram, session_factory):
        self.mock_download(telegram, self.FILE_ID)
        path = (
            Path("src/assets/animation/snap_finger") / f"animation_{self.FILE_ID}.mp4"
        )
        self.created.append(path)

        raw = message_update(
            "/add_gif snap",
            uid=ADMIN,
            reply_to_uid=42,
            reply_extra=self.animation_reply(),
        )
        await feed(raw)
        telegram.calls.clear()
        await feed(raw)

        assert telegram.sent == ["Запись в базе данных с таким файлом уже существует"]


class TestBroadcast:
    """telegram.sent собирает все sendMessage подряд (и «идёт рассылка», и сами
    сообщения получателям, и финальный отчёт) — отчёт админу всегда последний."""

    async def test_broadcast_private_counts_only_private_chat_users(
        self, send, session_factory
    ):
        await seed(session_factory, 42, "Вася", has_private_chat=True)
        await seed(session_factory, 43, "Петя", has_private_chat=False)

        texts = await send("/broadcast_private привет", uid=ADMIN)
        # получателей 2: seed(42) и сам админ — SyncEntitiesMiddleware завёл его
        # с has_private_chat=True (личка с ботом, раз он пишет команду в личке);
        # 43 (has_private_chat=False) в рассылку не попал
        assert "Всего: 2 | Успешно: 2 | Ошибок: 0" in texts[-1]

    async def test_broadcast_chats_targets_known_chats(
        self, feed, telegram, session_factory
    ):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        await feed(message_update("привет", uid=42, chat=-100123))  # заводит чат
        telegram.calls.clear()

        telegram = await feed(message_update("/broadcast_chats новости", uid=ADMIN))
        assert "Всего: 1 | Успешно: 1 | Ошибок: 0" in telegram.sent[-1]

    async def test_broadcast_all_sums_both(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася", has_private_chat=True)
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        await feed(message_update("привет", uid=43, chat=-100123))
        telegram.calls.clear()

        telegram = await feed(message_update("/broadcast_all всем", uid=ADMIN))
        # личка: 42 + сам админ (см. test_broadcast_private_*), плюс 1 чат
        assert "Всего: 3 | Успешно: 3 | Ошибок: 0" in telegram.sent[-1]

    async def test_broadcast_user_by_username(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        texts = await send("/broadcast_user @vasya привет лично", uid=ADMIN)
        assert texts[-1] == "✅ Сообщение отправлено."

    async def test_broadcast_user_not_found(self, send):
        (reply,) = await send("/broadcast_user @nobody текст", uid=ADMIN)
        assert "не найден" in reply

    async def test_missing_text_shows_usage(self, send):
        (reply,) = await send("/broadcast_private", uid=ADMIN)
        assert reply == "Использование: /broadcast_private <текст>"


class TestLevelUp:
    # GhoulService.get() (level_up/add_progress идут через него) считает
    # telegram_id > 666000 настоящим telegram_id, а меньшие — внутренним id гуля.
    UID = 700020

    async def ghoul(self, session_factory, telegram_id: int, **ghoul_fields):
        await seed(session_factory, telegram_id, "Вася", username="vasya")
        async with session_factory() as session:
            await GhoulRepository(session).upsert(
                telegram_id=telegram_id, **ghoul_fields
            )
            await session.commit()

    async def test_force_levelup_by_reply(self, feed, telegram, session_factory):
        await self.ghoul(session_factory, self.UID, level=3)

        telegram = await feed(
            message_update("/force_levelup", uid=ADMIN, reply_to_uid=self.UID)
        )
        # два сообщения: ЛС о левелапе адресату и подтверждение админу (последнее)
        assert telegram.sent[-1].startswith("✅ Уровень: 4.")
        ghoul = await get_ghoul(session_factory, self.UID)
        assert ghoul is not None and ghoul.level == 4

    async def test_force_levelup_explicit_no_ghoul(self, send, session_factory):
        await seed(session_factory, self.UID, "Вася", username="vasya")

        (reply,) = await send(f"/force_levelup {self.UID}", uid=ADMIN)
        assert reply.startswith("❌")

    async def test_force_levelup_target_not_found(self, send):
        (reply,) = await send("/force_levelup @nobody", uid=ADMIN)
        assert "не найден" in reply

    async def test_add_progress_by_reply_triggers_level_up(
        self, feed, telegram, session_factory
    ):
        await self.ghoul(session_factory, self.UID, level=3, level_progress=90)

        telegram = await feed(
            message_update("/add_progress 50", uid=ADMIN, reply_to_uid=self.UID)
        )
        assert "Уровней получено: 1" in telegram.sent[-1]
        ghoul = await get_ghoul(session_factory, self.UID)
        assert ghoul is not None and ghoul.level == 4

    async def test_add_progress_explicit_out_of_range(self, send, session_factory):
        await self.ghoul(session_factory, self.UID)

        assert await send(f"/add_progress {self.UID} 500", uid=ADMIN) == [
            "❌ Дельта должна быть в диапазоне от -100 до 100."
        ]

    async def test_add_progress_usage(self, send):
        (reply,) = await send("/add_progress", uid=ADMIN, reply_to_uid=self.UID)
        assert reply.startswith("Использование (реплаем")


class FakeNotifier:
    """Notifier без Telegram вообще — для юнит-тестов сервисов из services/,
    независимых от библиотеки (см. Notifier Protocol)."""

    def __init__(self, fail_for: frozenset[int] = frozenset()):
        self.sent: list[tuple[int, str]] = []
        self.fail_for = fail_for

    async def send_message(self, chat_id, text, *, parse_mode=None):
        if chat_id in self.fail_for:
            raise NotifyError("заблокировал бота")
        self.sent.append((chat_id, text))

    async def send_video(self, chat_id, video, *, caption=None):
        raise NotImplementedError


class TestBroadcastServiceUnit:
    """BroadcastService целиком независим от Telegram-библиотеки: ни разу не
    поднимает FakeTelegram, только FakeNotifier."""

    async def test_send_to_user_reports_failure_without_raising(self, session_factory):
        await seed(session_factory, 42, "Вася")

        async with session_factory() as session:
            service = BroadcastService(
                UserRepository(session),
                ChatRepository(session),
                FakeNotifier(frozenset({42})),
            )
            ok = await service.send_to_user(42, "привет")

        assert ok is False

    async def test_send_to_target_resolves_username(self, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        async with session_factory() as session:
            notifier = FakeNotifier()
            service = BroadcastService(
                UserRepository(session), ChatRepository(session), notifier
            )
            ok = await service.send_to_target("@vasya", "привет")

        assert ok is True
        assert notifier.sent == [(42, "привет")]


class TestSelfrotBotNotifier:
    """Единственное место, которое знает про selfrot.Bot: проверяем именно перевод
    ошибок Telegram в NotifyError, остальную логику — через FakeNotifier выше."""

    async def test_send_message_wraps_telegram_errors(self, telegram, dispatcher):
        telegram.errors["sendMessage"] = (403, "Forbidden: bot was blocked by the user")
        notifier = SelfrotBotNotifier(dispatcher.api)

        with pytest.raises(NotifyError):
            await notifier.send_message(42, "привет")

    async def test_send_message_succeeds(self, telegram, dispatcher):
        notifier = SelfrotBotNotifier(dispatcher.api)

        await notifier.send_message(42, "привет")

        (body,) = telegram.bodies("sendMessage")
        assert body["chat_id"] == 42 and body["text"] == "привет"
