"""
Логи порта: в консоль — всё от уровня LOG_LEVEL (по умолчанию INFO; DEBUG — всё,
что пишут бот и библиотеки, включая SQL), в файл — только WARNING и выше, с
ротацией. Прод писал в logs.log всё с DEBUG и растил его на мегабайты.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import colorlog

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
FILE_MAX_BYTES = 5 * 1024 * 1024
FILE_BACKUPS = 3


def console_level() -> int:
    name = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    level = logging.getLevelNamesMapping().get(name)
    if level is None:
        raise ValueError(
            f"LOG_LEVEL={name!r}: нужен один из DEBUG, INFO, WARNING, ERROR, CRITICAL"
        )
    return level


def setup_logging() -> None:
    level = console_level()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s" + FORMAT,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    )

    file = RotatingFileHandler(
        os.environ.get("LOG_FILE", "logs.log"),
        maxBytes=FILE_MAX_BYTES,
        backupCount=FILE_BACKUPS,
        encoding="utf-8",
    )
    file.setLevel(logging.WARNING)
    file.setFormatter(logging.Formatter(FORMAT))

    root = logging.getLogger()
    # Сбросить всё, что успели навесить до нас (basicConfig при импорте и т. п.).
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    root.setLevel(min(level, logging.WARNING))
    root.addHandler(console)
    root.addHandler(file)

    # SQLAlchemy при импорте сам ставит своему логгеру WARNING, и уровень корня до
    # него не доходит. В DEBUG — SQL и строки результатов; в INFO — как у SQLAlchemy,
    # иначе каждый запрос попадал бы в обычный лог.
    logging.getLogger("sqlalchemy").setLevel(
        logging.DEBUG if level <= logging.DEBUG else logging.WARNING
    )
