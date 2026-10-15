"""/rich реплаем на .md-файл: бот скачивает файл и отвечает rich-сообщением из этого
Markdown. Не тот файл — подсказка, отказ Telegram — его причина в ответе."""

from src.bot.dialogs import Dialogs

from .conftest import matches_phrase, message_update, only_text

MARKDOWN = "# Обновление\n\n- браки\n- `/rich`\n"


def rich_reply(file_name: str = "news.md", size: int = 64) -> dict:
    document = {"file_id": "D", "file_unique_id": "uD", "file_name": file_name, "file_size": size}
    return message_update("/rich", reply_to_uid=8, reply_extra={"document": document})


async def test_markdown_file_becomes_a_rich_message(feed, settle, telegram):
    telegram.results["getFile"] = {"file_id": "D", "file_unique_id": "uD", "file_path": "d/1"}
    telegram.set_file("d/1", MARKDOWN.encode())

    await feed(rich_reply())
    await settle()

    (body,) = telegram.bodies("sendRichMessage")
    assert body["rich_message"]["markdown"] == MARKDOWN


async def test_not_a_markdown_file_gets_the_usage(feed, telegram):
    await feed(rich_reply(file_name="photo.jpg"))

    (reply,) = telegram.sent
    assert reply == only_text(Dialogs.rich.usage())
    assert telegram.bodies("getFile") == []


async def test_markup_rejected_by_telegram_is_explained(feed, settle, telegram):
    telegram.results["getFile"] = {"file_id": "D", "file_unique_id": "uD", "file_path": "d/1"}
    telegram.set_file("d/1", MARKDOWN.encode())
    telegram.errors["sendRichMessage"] = (400, "Bad Request: can't parse rich message")

    await feed(rich_reply())
    await settle()

    (reply,) = telegram.sent
    assert matches_phrase(reply, "rich.rejected") and "can't parse" in reply
