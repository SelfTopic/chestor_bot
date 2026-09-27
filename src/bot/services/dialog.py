import logging
import random
from pathlib import Path

from src.bot.dialogs import (
    DIALOGS_DIR,
    PLACEHOLDERS,
    DialogFileError,
    Line,
    Placeholders,
    check_against,
    load_texts,
)

logger = logging.getLogger(__name__)


class DialogService:
    def __init__(
        self, folder: Path = DIALOGS_DIR, expected: Placeholders = PLACEHOLDERS
    ) -> None:
        self._folder = folder
        self._expected = expected
        self._stamp = self._files_stamp()
        self._texts = self._load()

    def text(self, line: Line) -> str:
        self._reload_if_changed()
        return random.choice(self._texts[line.key]).format_map(line.params)

    def _files_stamp(self) -> tuple[tuple[str, float], ...]:
        return tuple(
            (path.name, path.stat().st_mtime)
            for path in sorted(self._folder.glob("*.yaml"))
        )

    def _load(self) -> dict[str, tuple[str, ...]]:
        texts = load_texts(self._folder)
        check_against(texts, self._expected)
        return texts

    def _reload_if_changed(self) -> None:
        stamp = self._files_stamp()
        if stamp == self._stamp:
            return
        # Новый снимок запоминается и при ошибке: иначе предупреждение шло бы на каждый ответ.
        self._stamp = stamp
        try:
            self._texts = self._load()
        except (DialogFileError, OSError):
            logger.warning("Тексты не перечитаны, бот отвечает прежними", exc_info=True)
            return
        logger.info(f"Тексты перечитаны из {self._folder}: {len(self._texts)} фраз")


__all__ = ["DialogService"]
