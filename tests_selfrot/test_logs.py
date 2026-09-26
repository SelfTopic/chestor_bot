"""Логи: консоль — от LOG_LEVEL (DEBUG — всё), файл — только WARNING и выше."""

import logging

import pytest

from src.selfrot_bot.logs import setup_logging


@pytest.fixture
def root():
    """Корневой логгер без обработчиков pytest на время теста, потом как было."""
    logger = logging.getLogger()
    saved_handlers, saved_level = logger.handlers[:], logger.level
    for handler in saved_handlers:
        logger.removeHandler(handler)
    yield logger
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    for handler in saved_handlers:
        logger.addHandler(handler)
    logger.setLevel(saved_level)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)  # как ставит сама SQLAlchemy


@pytest.fixture
def log_file(tmp_path, monkeypatch):
    path = tmp_path / "logs.log"
    monkeypatch.setenv("LOG_FILE", str(path))
    return path


def emit_all() -> None:
    logging.getLogger("aiohttp.client").debug("GET /bot/getMe")
    logging.getLogger("sqlalchemy.engine").info("SELECT 1")
    logging.getLogger("sqlalchemy.pool").warning("пул переполнен")
    logging.getLogger("src.selfrot_bot").info("бот запущен")
    logging.getLogger("selfrot").warning("повтор getUpdates")
    logging.getLogger("src.selfrot_bot").error("хендлер упал")


def test_debug_shows_libraries_in_console_file_keeps_warnings(
    root, log_file, monkeypatch, capsys
):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    setup_logging()
    emit_all()

    console = capsys.readouterr().out
    for text in ("GET /bot/getMe", "бот запущен", "повтор getUpdates", "хендлер упал"):
        assert text in console
    saved = log_file.read_text()
    assert "GET /bot/getMe" not in saved and "бот запущен" not in saved
    assert "повтор getUpdates" in saved and "хендлер упал" in saved


def test_sqlalchemy_only_warnings_even_in_debug(root, log_file, monkeypatch, capsys):
    # SQL, пул и строки результатов забивали весь DEBUG-лог (DuelTicker — раз в секунду)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    setup_logging()
    emit_all()

    console = capsys.readouterr().out
    assert "SELECT 1" not in console
    assert "пул переполнен" in console


def test_default_is_info(root, log_file, monkeypatch, capsys):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    setup_logging()
    emit_all()

    console = capsys.readouterr().out
    assert "GET /bot/getMe" not in console
    assert "бот запущен" in console


def test_quiet_console_does_not_silence_the_file(root, log_file, monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    setup_logging()
    emit_all()

    assert "повтор getUpdates" not in capsys.readouterr().out
    assert "повтор getUpdates" in log_file.read_text()


def test_replaces_handlers_set_up_before(root, log_file, monkeypatch):
    logging.basicConfig(level=logging.DEBUG)  # как делает lottery_video_genertor при импорте
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    setup_logging()

    assert len(root.handlers) == 2


def test_typo_in_log_level_is_an_error(root, log_file, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBGU")

    with pytest.raises(ValueError, match="DEBGU"):
        setup_logging()
