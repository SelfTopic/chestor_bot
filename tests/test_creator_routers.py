"""routers/creator_routers: админ-команды за CreatorMiddleware. Админ — settings.ADMIN_IDS
(здесь uid=999, патчится autouse-фикстурой), проверка молчания для остальных — отдельно."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.bot.config import game_config
from src.bot.dialogs import Dialogs, Line, load_texts
from src.bot.repositories import (
    ChatRepository,
    GhoulRepository,
    MediaRepository,
    UserRepository,
)
from src.bot.types import KaguneType
from src.config import settings
from src.database.models import Cooldown, Media
from src.bot.routers.creator_routers.media import USAGE as ADD_GIF_USAGE
from src.bot.routers.creator_routers.stats_edits import USAGE as SET_STAT_USAGE
from src.bot.services.broadcast import BroadcastService
from src.bot.services.notify import NotifyError, SelfrotBotNotifier

from .conftest import matches_phrase, message_update, only_text, owner_dict
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
        assert matches_phrase(reply, "admin.ban.done")
        assert only_text(Dialogs.banned.forever()) in reply

        user = await get_user(session_factory, 42)
        assert user is not None and user.is_banned

    async def test_already_banned(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася", is_banned=True)

        telegram.calls.clear()
        await feed(message_update("/ban_bot причина", uid=ADMIN, reply_to_uid=42))

        assert telegram.sent == [only_text(Dialogs.admin.ban.already())]

    async def test_target_not_found(self, send):
        (reply,) = await send("/ban_bot @nobody", uid=ADMIN)
        assert reply == only_text(Dialogs.errors.user_not_found(query="@nobody"))

    async def test_unban_by_reply(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася", is_banned=True)

        await feed(message_update("/unban_bot", uid=ADMIN, reply_to_uid=42))

        user = await get_user(session_factory, 42)
        assert user is not None and not user.is_banned

    async def test_unban_explicit_not_banned(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        assert await send("/unban_bot @vasya", uid=ADMIN) == [
            only_text(Dialogs.admin.unban.not_banned())
        ]


class TestPlayersLookup:
    async def test_profile_found(self, send, session_factory):
        await seed(session_factory, 42, "Вася", balance=500)

        (reply,) = await send("/admin_profile 42", uid=ADMIN)
        assert matches_phrase(reply, "admin.profile.card")
        assert "Вася" in reply and "500" in reply
        assert only_text(Dialogs.admin.profile.active()) in reply
        assert only_text(Dialogs.admin.profile.banned()) not in reply

    async def test_banned_profile_shows_reason_and_term(self, send, session_factory):
        await seed(session_factory, 42, "Вася")
        await send("/ban_bot 42 читерство", uid=ADMIN)

        (reply,) = await send("/admin_profile 42", uid=ADMIN)
        ban = Dialogs.admin.profile.ban(
            reason="читерство", term=only_text(Dialogs.banned.forever())
        )
        assert only_text(Dialogs.admin.profile.banned()) + only_text(ban) in reply

    async def test_profile_not_found(self, send):
        assert await send("/admin_profile @nobody", uid=ADMIN) == [
            only_text(Dialogs.admin.profile.not_found())
        ]

    async def test_usage_on_missing_argument(self, send):
        (reply,) = await send("/admin_profile", uid=ADMIN)
        assert reply == only_text(Dialogs.admin.profile.usage())


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
        target = only_text(Dialogs.admin.stats.target_user())
        assert reply == only_text(
            Dialogs.admin.stats.done(field="balance", target=target, value=300)
        )

    async def test_ghoul_field(self, send, session_factory):
        await seed(session_factory, 42, "Вася")
        async with session_factory() as session:
            await GhoulRepository(session).upsert(telegram_id=42)
            await session.commit()

        (reply,) = await send("/set_stat 42 level 5", uid=ADMIN)
        target = only_text(Dialogs.admin.stats.target_ghoul())
        assert reply == only_text(
            Dialogs.admin.stats.done(field="level", target=target, value=5)
        )

        ghoul = await get_ghoul(session_factory, 42)
        assert ghoul is not None and ghoul.level == 5

    async def test_unknown_field(self, send, session_factory):
        await seed(session_factory, 42, "Вася")

        (reply,) = await send("/set_stat 42 nonsense 1", uid=ADMIN)
        assert reply == only_text(Dialogs.admin.stats.unknown_field(field="nonsense"))

    async def test_usage_lists_fields(self, send):
        (reply,) = await send("/set_stat", uid=ADMIN)
        assert reply == only_text(SET_STAT_USAGE)
        assert "hunger_hours_ago" in reply and "health_hours_ago" in reply


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
            only_text(Dialogs.admin.reset.no_ghoul())
        ]

    async def test_reset_user_explicit(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        (reply,) = await send("/reset_user @vasya", uid=ADMIN)
        assert matches_phrase(reply, "admin.reset.user_done")
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
        assert reply == only_text(Dialogs.admin.kill.done(id=42, cause="admin", deaths=1))

    async def test_kill_no_ghoul(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        (reply,) = await send("/kill_ghoul @vasya", uid=ADMIN)
        assert reply == only_text(Dialogs.admin.ghoul_not_found())

    async def test_kill_target_not_found(self, send):
        (reply,) = await send("/kill_ghoul @nobody", uid=ADMIN)
        assert reply == only_text(Dialogs.errors.user_not_found(query="@nobody"))


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

        assert telegram.sent == [only_text(Dialogs.admin.cooldown.cleared(type="SNAP"))]

    async def test_clear_all_explicit(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")
        await self.seed_cooldown(session_factory, 42)

        assert await send("/clear_cooldown @vasya all", uid=ADMIN) == [
            only_text(Dialogs.admin.cooldown.all_cleared(count=1))
        ]

    async def test_unknown_type(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        (reply,) = await send("/clear_cooldown @vasya nonsense", uid=ADMIN)
        assert matches_phrase(reply, "admin.cooldown.unknown_type")

    async def test_nothing_to_clear(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")
        # тип зарегистрирован (иначе была бы "неизвестный тип"), но активного нет
        async with session_factory() as session:
            session.add(Cooldown(name="OTHER", duration=60))
            await session.commit()

        (reply,) = await send("/clear_cooldown @vasya other", uid=ADMIN)
        assert matches_phrase(reply, "admin.cooldown.not_active")


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
        assert matches_phrase(reply, "admin.kagune.given")

    async def test_give_unknown_type(self, send, session_factory):
        await self.seed_ghoul(session_factory, self.UID)

        (reply,) = await send("/give_kagune @vasya nonsense", uid=ADMIN)
        assert matches_phrase(reply, "admin.kagune.unknown_type_or_all")

    async def test_remove(self, send, session_factory):
        await self.seed_ghoul(session_factory, self.UID)
        first = next(iter(KaguneType))

        # нельзя убрать последний оставшийся тип, поэтому сначала выдаём все
        await send("/give_kagune @vasya all", uid=ADMIN)
        (reply,) = await send(
            f"/remove_kagune @vasya {first.value['name_english']}", uid=ADMIN
        )

        assert matches_phrase(reply, "admin.kagune.removed")


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
                "/add_gif snap.done",
                uid=ADMIN,
                reply_to_uid=42,
                reply_extra=self.animation_reply(),
            )
        )

        assert path.exists() and path.read_bytes() == b"gif-bytes"
        (sent,) = telegram.bodies("sendAnimation")
        assert matches_phrase(sent["caption"], "admin.media.saved")

        # ответ — та же гифка по file_id, без повторной загрузки: один file_unique_id
        assert sent["animation"] == self.FILE_ID

        row = await self.get_media_row(session_factory, str(path))
        assert row is not None
        assert row.telegram_file_id == self.FILE_ID
        assert row.file_unique_id == "u"
        assert row.collection == "snap.done"
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

    def test_phrase_gif_folder_takes_its_placeholder(self, dispatcher):
        # на диск не пишем: часть src/assets в этом окружении принадлежит root
        gifs = dispatcher.dialog_service.gifs(
            Line("kagune.upgrade.done", {"kagune": "ukaku"})
        )

        assert gifs.folder == Path("src/assets/animation/upgrade_kagune/ukaku")

    async def test_phrase_folder_placeholder_is_required(self, send, telegram):
        (reply,) = await send(
            "/add_gif kagune.upgrade.done",
            uid=ADMIN,
            reply_to_uid=42,
            reply_extra=self.animation_reply(),
        )

        assert reply == only_text(
            Dialogs.admin.media.missing_param(key="kagune.upgrade.done", name="kagune")
        )
        assert telegram.downloads == []

    async def test_section_lists_its_phrases(self, send, telegram):
        (reply,) = await send(
            "/add_gif coffee",
            uid=ADMIN,
            reply_to_uid=42,
            reply_extra=self.animation_reply(),
        )

        keys = "\n".join(key for key in sorted(load_texts()) if key.startswith("coffee."))
        assert reply == only_text(Dialogs.admin.media.section(section="coffee", keys=keys))
        assert telegram.downloads == []

    async def test_typo_suggests_the_phrase(self, send):
        (reply,) = await send(
            "/add_gif coffee.don",
            uid=ADMIN,
            reply_to_uid=42,
            reply_extra=self.animation_reply(),
        )

        assert matches_phrase(reply, "admin.media.did_you_mean")
        assert "coffee.done" in reply

    async def test_new_placeholder_value_needs_confirmation(
        self, send, feed, telegram, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        (tmp_path / "animation" / "upgrade_kagune" / "ukaku").mkdir(parents=True)
        self.mock_download(telegram, self.FILE_ID)

        (reply,) = await send(
            "/add_gif kagune.upgrade.done kagune=ukku",
            uid=ADMIN,
            reply_to_uid=42,
            reply_extra=self.animation_reply(),
        )

        unknown = Dialogs.admin.media.unknown_value(
            key="kagune.upgrade.done", name="kagune", value="ukku", known="ukaku"
        )
        assert reply == only_text(unknown)
        assert telegram.downloads == []

        await feed(
            message_update(
                "/add_gif kagune.upgrade.done kagune=koukaku!",
                uid=ADMIN,
                reply_to_uid=42,
                reply_extra=self.animation_reply(),
            )
        )
        saved = tmp_path / "animation" / "upgrade_kagune" / "koukaku"
        assert (saved / f"animation_{self.FILE_ID}.mp4").exists()

    async def test_unknown_collection(self, feed, telegram):
        telegram_response = await feed(
            message_update(
                "/add_gif nonsense",
                uid=ADMIN,
                reply_to_uid=42,
                reply_extra=self.animation_reply(),
            )
        )

        assert matches_phrase(telegram_response.sent[0], "admin.media.unknown_collection")
        assert telegram.downloads == []  # до скачивания не дошло

    async def test_no_media_in_reply(self, send):
        assert await send("/add_gif snap", uid=ADMIN, reply_to_uid=42) == [
            only_text(Dialogs.admin.media.no_media())
        ]

    async def test_missing_collection_argument(self, send):
        assert await send(
            "/add_gif", uid=ADMIN, reply_to_uid=42, reply_extra=self.animation_reply()
        ) == [send.dispatcher.dialog_service.text(ADD_GIF_USAGE)]

    async def test_no_reply_is_ignored(self, send):
        assert await send("/add_gif snap", uid=ADMIN) == []

    async def test_duplicate_path_is_rejected(self, feed, telegram, session_factory):
        self.mock_download(telegram, self.FILE_ID)
        path = (
            Path("src/assets/animation/snap_finger") / f"animation_{self.FILE_ID}.mp4"
        )
        self.created.append(path)

        raw = message_update(
            "/add_gif snap.done",
            uid=ADMIN,
            reply_to_uid=42,
            reply_extra=self.animation_reply(),
        )
        await feed(raw)
        telegram.calls.clear()
        await feed(raw)

        assert telegram.sent == [only_text(Dialogs.admin.media.exists())]


class TestRemoveGif:
    async def stored_gif(self, session_factory, tmp_path) -> Path:
        path = tmp_path / "animation_OLD.mp4"
        path.write_bytes(b"gif-bytes")
        async with session_factory() as session:
            session.add(
                Media(
                    media_type="animation",
                    telegram_file_id="OLD_FILE_ID",
                    file_unique_id="UNIQUE",
                    collection="coffee.done",
                    path=str(path),
                    uploaded_by=ADMIN,
                )
            )
            await session.commit()
        return path

    def gif(self, file_unique_id: str) -> dict:
        # file_id у одного файла в разных сообщениях разный, file_unique_id — тот же
        return {
            "animation": {
                "file_id": "ANOTHER_FILE_ID",
                "file_unique_id": file_unique_id,
                "width": 1,
                "height": 1,
                "duration": 1,
            }
        }

    async def test_removes_file_and_row(self, send, session_factory, tmp_path):
        path = await self.stored_gif(session_factory, tmp_path)

        (reply,) = await send(
            "/remove_gif", uid=ADMIN, reply_to_uid=42, reply_extra=self.gif("UNIQUE")
        )

        assert reply == only_text(Dialogs.admin.media.removed(paths=str(path)))
        assert not path.exists()
        async with session_factory() as session:
            assert await MediaRepository(session).get_by_path(str(path)) is None

    async def test_unknown_gif(self, send, session_factory, tmp_path):
        path = await self.stored_gif(session_factory, tmp_path)

        (reply,) = await send(
            "/remove_gif", uid=ADMIN, reply_to_uid=42, reply_extra=self.gif("OTHER")
        )

        assert reply == only_text(Dialogs.admin.media.remove_not_found())
        assert path.exists()

    async def test_without_reply_shows_usage(self, send):
        assert await send("/remove_gif", uid=ADMIN) == [
            only_text(Dialogs.admin.media.remove_usage())
        ]


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
        assert texts[-1] == only_text(
            Dialogs.admin.broadcast.finished(total=2, success=2, failed=0)
        )

    async def test_broadcast_chats_targets_known_chats(
        self, feed, telegram, session_factory
    ):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        await feed(message_update("привет", uid=42, chat=-100123))  # заводит чат
        telegram.calls.clear()

        telegram = await feed(message_update("/broadcast_chats новости", uid=ADMIN))
        assert telegram.sent[-1] == only_text(
            Dialogs.admin.broadcast.finished(total=1, success=1, failed=0)
        )

    async def test_broadcast_all_sums_both(self, feed, telegram, session_factory):
        await seed(session_factory, 42, "Вася", has_private_chat=True)
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        await feed(message_update("привет", uid=43, chat=-100123))
        telegram.calls.clear()

        telegram = await feed(message_update("/broadcast_all всем", uid=ADMIN))
        # личка: 42 + сам админ (см. test_broadcast_private_*), плюс 1 чат
        assert telegram.sent[-1] == only_text(
            Dialogs.admin.broadcast.finished(total=3, success=3, failed=0)
        )

    async def test_broadcast_user_by_username(self, send, session_factory):
        await seed(session_factory, 42, "Вася", username="vasya")

        texts = await send("/broadcast_user @vasya привет лично", uid=ADMIN)
        assert texts[-1] == only_text(Dialogs.admin.broadcast.sent())

    async def test_broadcast_user_not_found(self, send):
        (reply,) = await send("/broadcast_user @nobody текст", uid=ADMIN)
        assert reply == only_text(Dialogs.errors.user_not_found(query="@nobody"))

    async def test_missing_text_shows_usage(self, send):
        (reply,) = await send("/broadcast_private", uid=ADMIN)
        assert reply == only_text(Dialogs.admin.broadcast.private_usage())


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
        assert matches_phrase(telegram.sent[-1], "admin.level_up.done")
        ghoul = await get_ghoul(session_factory, self.UID)
        assert ghoul is not None and ghoul.level == 4

    async def test_force_levelup_explicit_no_ghoul(self, send, session_factory):
        await seed(session_factory, self.UID, "Вася", username="vasya")

        (reply,) = await send(f"/force_levelup {self.UID}", uid=ADMIN)
        assert reply == only_text(Dialogs.admin.ghoul_not_found())

    async def test_force_levelup_target_not_found(self, send):
        (reply,) = await send("/force_levelup @nobody", uid=ADMIN)
        assert reply == only_text(Dialogs.errors.user_not_found(query="@nobody"))

    async def test_add_progress_by_reply_triggers_level_up(
        self, feed, telegram, session_factory
    ):
        await self.ghoul(session_factory, self.UID, level=3, level_progress=90)

        telegram = await feed(
            message_update("/add_progress 50", uid=ADMIN, reply_to_uid=self.UID)
        )
        progress, _level_line = telegram.sent[-1].split("\n")
        assert matches_phrase(progress, "admin.progress.done")
        ghoul = await get_ghoul(session_factory, self.UID)
        assert ghoul is not None and ghoul.level == 4

    async def test_add_progress_explicit_out_of_range(self, send, session_factory):
        await self.ghoul(session_factory, self.UID)

        assert await send(f"/add_progress {self.UID} 500", uid=ADMIN) == [
            only_text(Dialogs.admin.progress.delta_range())
        ]

    async def test_add_progress_usage(self, send):
        (reply,) = await send("/add_progress", uid=ADMIN, reply_to_uid=self.UID)
        assert reply == only_text(Dialogs.admin.progress.replied_usage())


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
