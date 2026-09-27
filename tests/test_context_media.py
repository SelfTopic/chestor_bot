"""AppContext.answer_gif/reply_gif: общий хелпер для гифок с кэшем telegram_file_id,
рассчитанный на переиспользование в любом будущем роутере (common/moderator/ghoul),
который шлёт гифки — не только в ghoul_routers. Сама отправка идёт через selfrot
(ctx.answer_animation/reply_animation), кэш — через ctx.media_repository, уже
переиспользуемый в порте (см. context.py). Тот же приём уже есть у NotificationTicker
для видео (test_notification_ticker.py), там он проверяется через FakeNotifier —
здесь идём через настоящий FakeTelegram (нет Notifier-абстракции для reply/answer
внутри хендлера), поэтому conftest.FakeTelegram.fail_next имитирует протухший id."""

import pytest
from selfrot import MessageHandler
from selfrot.filter import HasText, Text
from selfrot.types import TextMessage

from src.bot.dialogs import Line
from src.bot.repositories import MediaRepository
from src.bot.services.dialog import DialogService
from src.database.models import Media
from src.bot.__main__ import Dispatcher
from src.bot.context import AppContext

from .conftest import message_update

_GIF: Media | None = None


class AnswerGifHandler(MessageHandler[AppContext[TextMessage]]):
    query = Text("гиф", ignore_case=True)

    async def handle(self) -> None:
        assert _GIF is not None
        await self.ctx.answer_gif(_GIF, caption="привет")


class ReplyGifHandler(MessageHandler[AppContext[TextMessage]]):
    query = Text("гиф в ответ", ignore_case=True)

    async def handle(self) -> None:
        assert _GIF is not None
        await self.ctx.reply_gif(_GIF, caption="привет")


class GifDispatcher(Dispatcher):
    handlers = (ReplyGifHandler, AnswerGifHandler)


def animation_result(chat_id: int, file_id: str) -> dict:
    return {
        "message_id": 1,
        "date": 5,
        "chat": {"id": chat_id, "type": "private"},
        "animation": {
            "file_id": file_id,
            "file_unique_id": "u",
            "width": 1,
            "height": 1,
            "duration": 1,
        },
    }


class TestAnswerAndReplyGif:
    @pytest.fixture
    def gif_file(self, tmp_path):
        path = tmp_path / "test.mp4"
        path.write_bytes(b"gif-bytes")
        return path

    async def test_sends_cached_file_id_without_reuploading(
        self, feed, telegram, gif_file, session_factory
    ):
        global _GIF
        _GIF = Media(
            media_type="animation",
            telegram_file_id="CACHED_ID",
            collection="test",
            path=str(gif_file),
            uploaded_by=1,
        )
        telegram.results["sendAnimation"] = animation_result(42, "CACHED_ID")
        dp = GifDispatcher(token="1:TEST", session_factory=session_factory)

        await feed(message_update("гиф", uid=42), dp)
        await dp.api.close_session()

        (body,) = telegram.bodies("sendAnimation")
        assert body["animation"] == "CACHED_ID"

    async def test_first_upload_fills_the_cache(
        self, feed, telegram, gif_file, session_factory
    ):
        # у прода первая заливка с диска в кэш не попадала: гифка каждый раз
        # грузилась заново, пока Telegram не отвергнет устаревший id
        global _GIF
        async with session_factory() as session:
            session.add(
                Media(
                    media_type="animation",
                    telegram_file_id=None,
                    collection="test",
                    path=str(gif_file),
                    uploaded_by=1,
                )
            )
            await session.commit()
            _GIF = await MediaRepository(session).get_by_path(str(gif_file))
        telegram.results["sendAnimation"] = animation_result(42, "FRESH_ID")
        dp = GifDispatcher(token="1:TEST", session_factory=session_factory)

        await feed(message_update("гиф", uid=42), dp)
        await dp.api.close_session()

        (body,) = telegram.bodies("sendAnimation")
        assert body["animation"] == "<file:test.mp4>"

        async with session_factory() as session:
            media = await MediaRepository(session).get_by_path(str(gif_file))
        assert media is not None and media.telegram_file_id == "FRESH_ID"

    async def test_stale_file_id_reuploads_and_updates_cache(
        self, feed, telegram, gif_file, session_factory
    ):
        global _GIF
        async with session_factory() as session:
            session.add(
                Media(
                    media_type="animation",
                    telegram_file_id="STALE_ID",
                    collection="test",
                    path=str(gif_file),
                    uploaded_by=1,
                )
            )
            await session.commit()
            _GIF = await MediaRepository(session).get_by_path(str(gif_file))

        telegram.fail_next("sendAnimation", "animation", "STALE_ID")
        telegram.results["sendAnimation"] = animation_result(42, "NEW_ID")
        dp = GifDispatcher(token="1:TEST", session_factory=session_factory)

        await feed(message_update("гиф", uid=42), dp)
        await dp.api.close_session()

        first, second = telegram.bodies("sendAnimation")
        assert first["animation"] == "STALE_ID"
        assert second["animation"] == "<file:test.mp4>"

        async with session_factory() as session:
            media = await MediaRepository(session).get_by_path(str(gif_file))
        assert media is not None and media.telegram_file_id == "NEW_ID"

    async def test_reply_gif_replies_to_triggering_message(
        self, feed, telegram, gif_file, session_factory
    ):
        global _GIF
        _GIF = Media(
            media_type="animation",
            telegram_file_id="CACHED_ID",
            collection="test",
            path=str(gif_file),
            uploaded_by=1,
        )
        telegram.results["sendAnimation"] = animation_result(42, "CACHED_ID")
        dp = GifDispatcher(token="1:TEST", session_factory=session_factory)

        await feed(message_update("гиф в ответ", uid=42), dp)
        await dp.api.close_session()

        (body,) = telegram.bodies("sendAnimation")
        assert body["reply_parameters"]["message_id"] == 1


class SayHandler(MessageHandler[AppContext[TextMessage]]):
    query = HasText()

    async def handle(self) -> None:
        await self.ctx.say(Line(self.ctx.message.text, {}), reply=True)


class SayDispatcher(Dispatcher):
    handlers = (SayHandler,)


class TestSay:
    PHRASES = {"hello": frozenset(), "rare": frozenset(), "long": frozenset()}

    @pytest.fixture
    def dispatcher_with_gifs(self, tmp_path, session_factory):
        (tmp_path / "texts.yaml").write_text(
            "hello:\n  gifs: shared\n  text: Привет\n"
            "rare:\n  gifs: shared\n  gif_chance: 0\n  text: Редко\n"
            f"long:\n  gifs: shared\n  text: {'а' * 1100}\n",
            "utf-8",
        )
        folder = tmp_path / "animation" / "shared"
        folder.mkdir(parents=True)
        (folder / "hello.mp4").write_bytes(b"gif-bytes")

        dp = SayDispatcher(token="1:TEST", session_factory=session_factory)
        dp.dialog_service = DialogService(
            tmp_path, self.PHRASES, animation_root=tmp_path / "animation"
        )
        return dp

    async def test_phrase_with_gifs_is_a_captioned_animation(
        self, feed, telegram, dispatcher_with_gifs
    ):
        telegram.results["sendAnimation"] = animation_result(42, "NEW_ID")

        await feed(message_update("hello", uid=42), dispatcher_with_gifs)
        (first,) = telegram.bodies("sendAnimation")
        await feed(message_update("hello", uid=42), dispatcher_with_gifs)
        (second,) = telegram.bodies("sendAnimation")
        await dispatcher_with_gifs.api.close_session()

        assert first["caption"] == "Привет" and first["reply_parameters"]
        assert first["animation"] == "<file:hello.mp4>"
        assert second["animation"] == "NEW_ID"
        assert telegram.sent == []

    @pytest.mark.parametrize("phrase", ["rare", "long"])
    async def test_zero_chance_or_caption_too_long_is_plain_text(
        self, feed, telegram, dispatcher_with_gifs, phrase
    ):
        await feed(message_update(phrase, uid=42), dispatcher_with_gifs)
        await dispatcher_with_gifs.api.close_session()

        assert telegram.bodies("sendAnimation") == []
        assert len(telegram.sent) == 1
