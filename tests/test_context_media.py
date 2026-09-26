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
from selfrot.filter import Text
from selfrot.types import TextMessage

from src.bot.repositories import MediaRepository
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

    async def test_first_upload_without_cache_is_not_cached(
        self, feed, telegram, gif_file, session_factory
    ):
        # прод-особенность (сохранена как есть, см. context.py/_send_gif): если
        # кэша ещё не было, первая заливка с диска не попадает в media_repository —
        # кэш заполняется только веткой retry ниже.
        global _GIF
        _GIF = Media(
            media_type="animation",
            telegram_file_id=None,
            collection="test",
            path=str(gif_file),
            uploaded_by=1,
        )
        telegram.results["sendAnimation"] = animation_result(42, "FRESH_ID")
        dp = GifDispatcher(token="1:TEST", session_factory=session_factory)

        await feed(message_update("гиф", uid=42), dp)
        await dp.api.close_session()

        (body,) = telegram.bodies("sendAnimation")
        assert body["animation"] == "<file:test.mp4>"

        async with session_factory() as session:
            media = await MediaRepository(session).get_by_path(str(gif_file))
        assert media is None

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
